import os
import time
import sounddevice as sd
import requests
import soundfile as sf
import azure.cognitiveservices.speech as speechsdk
import numpy as np
from openai import AzureOpenAI
from collections import deque
from io import BytesIO


# ================== Configuration ==================
AZURE_SPEECH_KEY = os.environ["AZURE_SPEECH_KEY"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_SERVICE_REGION = "westeurope"
TTS_VOICE_NAME = "en-US-JennyNeural"
AZURE_OPENAI_ENDPOINT = "https://storegpt-ai-service-1.openai.azure.com/"

CONVERSATION_HISTORY_MAX = 6
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024

# ================== Global State ==================
conversation_history = deque(maxlen=CONVERSATION_HISTORY_MAX)
is_speaking = False

# ================== Initialize Clients ==================
openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-05-01-preview"
)

speech_config = speechsdk.SpeechConfig(
    subscription=AZURE_SPEECH_KEY,
    region=AZURE_SERVICE_REGION
)

# ================== Core Functions ==================
def speech_to_text_continuous():
    """Robust speech recognition with audio format validation"""
    audio_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    recognized_text = []
    
    def record_callback(indata, frames, time, status):
        try:
            if not is_speaking:
                audio_stream.write(indata.tobytes())
        except Exception as e:
            print(f"Audio stream error: {str(e)}")
    
    def recognized_callback(evt):
        if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
            recognized_text.append(evt.result.text)
    
    recognizer.recognized.connect(recognized_callback)
    recognizer.start_continuous_recognition()
    
    with sd.InputStream(callback=record_callback, 
                       blocksize=CHUNK_SIZE,
                       samplerate=SAMPLE_RATE,
                       channels=1,
                       dtype='int16'):
        while not recognized_text:
            time.sleep(0.1)
    
    recognizer.stop_continuous_recognition()
    return " ".join(recognized_text)

def text_to_speech(text):
    """Robust text-to-speech with format conversion"""
    global is_speaking
    
    try:
        is_speaking = True
        
        headers = {
            "Ocp-Apim-Subscription-Key": AZURE_SPEECH_KEY,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"
        }

        ssml = f"""
        <speak version='1.0' xml:lang='en-US'>
            <voice name='{TTS_VOICE_NAME}'>
                <prosody rate="1.0" pitch="0%">{text}</prosody>
            </voice>
        </speak>
        """
        
        response = requests.post(
            f"https://{AZURE_SERVICE_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
            headers=headers, 
            data=ssml.encode("utf-8"),
            timeout=10
        )
        
        if response.status_code == 200:
            with BytesIO(response.content) as audio_data:
                data, samplerate = sf.read(audio_data)
                
                # Convert to 32-bit float and ensure proper shape
                data = data.astype('float32')
                if data.ndim == 1:
                    data = data[:, np.newaxis]
                
                # Blocking playback with format validation
                with sd.OutputStream(samplerate=samplerate, 
                                    channels=data.shape[1],
                                    dtype='float32') as stream:
                    stream.write(data)
        
        else:
            print(f"TTS failed with status {response.status_code}")
            
    except Exception as e:
        print(f"TTS error: {str(e)}")
    finally:
        is_speaking = False

def chat_with_llm(prompt):
    """Complete LLM interaction with conversation history"""
    global conversation_history
    
    system_message = {
        "role": "system",
        "content": [{
            "type": "text", 
            "text": """You're a conversational assistant. Respond naturally with:
            - Contextual follow-ups
            - Concise responses (1-2 sentences)
            - Natural conversation flow"""
        }]
    }
    
    conversation_history.append({"role": "user", "content": [{"type": "text", "text": prompt}]})
    
    messages = [system_message] + list(conversation_history)[-CONVERSATION_HISTORY_MAX:]
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=150,
        temperature=0.7,
        presence_penalty=0.5,
        frequency_penalty=0.5
    )
    
    assistant_response = response.choices[0].message.content
    conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": assistant_response}]})
    
    return assistant_response

# ================== Main Loop ==================
def main():
    print("Voice Assistant Ready - Speak Naturally!")
    
    while True:
        try:
            if not is_speaking:
                user_input = speech_to_text_continuous()
                print(f"\nUser: {user_input}")
                
                response = chat_with_llm(user_input)
                print(f"\nAssistant: {response}")
                
                text_to_speech(response)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Main loop error: {str(e)}")
            time.sleep(1)

if __name__ == "__main__":
    main()