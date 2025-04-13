import os
import time
import threading
import sounddevice as sd
import requests
import soundfile as sf
import azure.cognitiveservices.speech as speechsdk
import numpy as np
from openai import AzureOpenAI
from collections import deque
from io import BytesIO
from datetime import datetime

# ================== Configuration ==================
AZURE_SPEECH_KEY = "Azure-Speech-Key"  # Replace with your Azure Speech Service key
AZURE_OPENAI_API_KEY = "<Azure-OpenAI-Key>"
AZURE_SERVICE_REGION = "westeurope"
TTS_VOICE_NAME = "en-US-JennyNeural"
AZURE_OPENAI_ENDPOINT = "https://storegpt-ai-service-1.openai.azure.com/"

CONVERSATION_HISTORY_MAX = 6
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
VOICE_INTERRUPT_THRESHOLD = 15000  # Adjust based on your environment
INTERRUPT_DELAY_SEC = 3  # New: delay before interruptions are checked

# ================== Global State ==================
conversation_history = deque(maxlen=CONVERSATION_HISTORY_MAX)
is_speaking = False
interrupt_tts = False  # Flag to signal TTS interruption
tts_start_time = 0  # New: record when TTS started

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

# ================== New Feature: Background Monitoring for Interruptions ==================
def monitor_interruptions():
    """Continuously monitor the microphone input to detect if user starts speaking during TTS."""
    def interruption_callback(indata, frames, time_info, status):
        global interrupt_tts, is_speaking, tts_start_time
        # Only check for interruptions when assistant is speaking and after a short delay
        if is_speaking and (time.time() - tts_start_time > INTERRUPT_DELAY_SEC):
            if np.max(np.abs(indata)) > VOICE_INTERRUPT_THRESHOLD:
                print('np.max(np.abs(indata))',np.max(np.abs(indata)))
                interrupt_tts = True

    # Open a continuous input stream for interruption detection
    with sd.InputStream(callback=interruption_callback, 
                        blocksize=CHUNK_SIZE,
                        samplerate=SAMPLE_RATE,
                        channels=1,
                        dtype='int16'):
        while True:
            time.sleep(0.1)

# Start the monitoring thread (daemon so it exits with the main program)
interrupt_thread = threading.Thread(target=monitor_interruptions, daemon=True)
interrupt_thread.start()

import socketio
import time

import socketio
import time
import atexit

# Global Socket.IO client instance
sio = socketio.Client()
SOCKET_SERVER_URL = "http://localhost:5000/test"
SOCKET_EVENT_NAME = "highlight"

def setup_connection():
    """Initialize and maintain persistent connection"""
    if not sio.connected:
        try:
            print("⚡ Establishing persistent connection to server...")
            sio.connect(SOCKET_SERVER_URL, namespaces=['/test'])
            
            # Wait for connection to stabilize
            # while not sio.connected or '/test' not in sio.namespaces:
            #     time.sleep(0.1)
                
            print(f"✅ Connected to namespaces: {sio.namespaces}")
            
            # Register cleanup at exit
            atexit.register(cleanup_connection)
            
        except Exception as e:
            print(f"❌ Initial connection failed: {e}")
            raise

def cleanup_connection():
    """Cleanly disconnect when application exits"""
    if sio.connected:
        print("♻️ Closing persistent connection...")
        sio.disconnect()

def highlight(text):
    """Highlight text using the persistent connection"""
    if not sio.connected:
        setup_connection()
    
    try:
        # Verify namespace is still active
        if '/test' not in sio.namespaces:
            print("⚠️ Namespace disconnected, reconnecting...")
            setup_connection()
        
        print(f"🔥 Sending highlight event: {text}")
        sio.emit('highlight', {"id": text}, namespace='/test')
        
    except Exception as e:
        print(f"❌ Emit failed: {e}")
        # Attempt to reconnect on failure
        try:
            setup_connection()
            sio.emit('highlight', {"id": text}, namespace='/test')
        except Exception as retry_e:
            print(f"❌ Retry failed: {retry_e}")

# Initialize connection when module loads
setup_connection()


# ================== Core Functions ==================
def speech_to_text_continuous():
    """Robust speech recognition with audio format validation"""
    audio_stream = speechsdk.audio.PushAudioInputStream()
    audio_config = speechsdk.audio.AudioConfig(stream=audio_stream)
    recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
    
    recognized_text = []
    
    def record_callback(indata, frames, time_info, status):
        try:
            # Only record user input when not speaking (TTS not active)
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
    """Robust text-to-speech with format conversion and interruption support"""
    global is_speaking, interrupt_tts, tts_start_time
    try:
        is_speaking = True
        interrupt_tts = False  # Reset interruption flag
        tts_start_time = time.time()  # Record when TTS starts
        
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
                
                data = data.astype('float32')
                if data.ndim == 1:
                    data = data[:, np.newaxis]
                
                with sd.OutputStream(samplerate=samplerate, 
                                     channels=data.shape[1],
                                     dtype='float32') as stream:
                    chunk_size = 1024
                    for i in range(0, len(data), chunk_size):
                        if interrupt_tts:
                            print("TTS Interrupted by user input")
                            break
                        stream.write(data[i: i+chunk_size])
        else:
            print(f"TTS failed with status {response.status_code}")
            
    except Exception as e:
        print(f"TTS error: {str(e)}")
    finally:
        is_speaking = False
        interrupt_tts = False  # Reset for next cycle

from rag import fetch_relevant_documents
# ... [other imports remain unchanged]

html_content_and_id_pair = '''
[
    {
        "id": "testIntro",
        "text": "A complete AI-powered recruiting solution. From candidate sourcing and screening to interview coordination, Apli automates recruiting so you can hire better and faster."
    },
    {
        "id": "idAbout",
        "text": "About. Instead of competing for applicants on job boards, Apli advertises your job to millions on social media. Our chatbots screen candidates at scale with customizable assessments."
    },
    {
        "id": "idChatbot",
        "text": "Candidate Chatbot. Screens candidates via bot mimicking expert recruiters. Handles pre-screening, assessments, interviews, document gathering, and onboarding in one conversation."
    },
    {
        "id": "idIntegrations",
        "text": "Integrations. Works with Success Factors, Cornerstone, Workday, Slack, and G-Suite."
    },
    {
        "id": "testId",
        "text": "Pricing is 600 Rs for 1 hr and there is subscription model available, if you want to use for 1 month then pay 6000"
    }
]
'''

def get_html_element_info(query):
    import json
    import re
    """Complete LLM interaction with conversation history,
    enriched with relevant company info from the RAG DB."""
    global conversation_history

    conversation_history.append({
    "role": "user",
    "content": [{"type": "text", "text": query}]
    })
    
    conversation_history = list(conversation_history)[-CONVERSATION_HISTORY_MAX:]

    prompt_template = f"""
        You are a conversational expert and a demo assitant for a SAAS product. Your job is to provide a product walk through along with the business context.
        I am providing you with the list of json objects and the user conversation history, each json object having two things 
        1. id of the html block (like para, header) from the SAAS product
        2. text of the same html block, from the same SAAD product  

        Your task:
        - Identify the jsons that corresponds to the query and conside the user conversation history. Provide concise responses (1-2 sentences)
        - Provide id of the element (if available).
        - Since You're a conversational assistant. Respond naturally with:
        - Contextual follow-ups
        - Concise responses (1-2 sentences)
        - Natural conversation flow

        ### HTML:
        {html_content_and_id_pair}

        ### Conversation History:
        {conversation_history}

        ### Query:
        "{query}"

        ### Output format (json format, without json word and ```, pure json wrapped inside brackets):
        ID: <Element ID (or "N/A" if no ID)>
        Conversational_Response : <Clear, client-centric explanation of the section’s content and value>
        """
    
    messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt_template}
        ]

    # Call the LLM
    now = datetime.now()
    print('now_rag', now)
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=150,
        temperature=0.7,
        presence_penalty=0.5,
        frequency_penalty=0.5
    )
    print('now_rag', datetime.now()-now)
    now = datetime.now()

    # Extract and print the response
    content = response.choices[0].message.content

    print('content', content)
    json_content = json.loads(content)
    print('json_content', json_content)

    return json_content['ID'], json_content['Conversational_Response']


def chat_with_llm(prompt):
    import json
    import socketio

    id, conversatio_text = get_html_element_info(prompt)
    highlight(id)

    ## call highlight method or the API call here, get the id from html_element_info json and call higlight
    
    # First, fetch relevant documents based on the prompt.
    # relevant_docs = fetch_relevant_documents(prompt)
    # print('relevant_docs', len(relevant_docs))
    # # print('relevant_docs', relevant_docs)
    # context_prompt = ""
    # if relevant_docs:
    #     context_prompt = "Relevant company info:\n" + "\n".join(relevant_docs) + "\n"
    
    # system_message = {
    #     "role": "system",
    #     "content": [{
    #         "type": "text",
    #         "text": (
    #             "You're a conversational assistant. Respond naturally with:\n"
    #             "- Contextual follow-ups\n"
    #             "- Concise responses (1-2 sentences)\n"
    #             "- Natural conversation flow"
    #         )
    #     }]
    # }
    
    # # Combine the context with the user prompt.
    # full_prompt = context_prompt + prompt
    # conversation_history.append({
    #     "role": "user",
    #     "content": [{"type": "text", "text": full_prompt}]
    # })
    
    # messages = [system_message] + list(conversation_history)[-CONVERSATION_HISTORY_MAX:]
    
    # now_query = datetime.now()
    # response = openai_client.chat.completions.create(
    #     model="gpt-4o",
    #     messages=messages,
    #     max_tokens=150,
    #     temperature=0.7,
    #     presence_penalty=0.5,
    #     frequency_penalty=0.5
    # )
    # print('now_query', datetime.now() - now_query)
    
    # assistant_response = response.choices[0].message.content

    conversation_history.append({
        "role": "assistant",
        "content": [{"type": "text", "text": conversatio_text}]
    })
    
    return conversatio_text


# ================== Main Loop ==================
def main():
    print("Voice Assistant Ready - Speak Naturally!")
    
    while True:
        try:
            # Only listen for new input when not currently speaking (TTS not active)
            if not is_speaking:
                user_input = speech_to_text_continuous()
                print(f"\nUser: {user_input}")
                
                response = chat_with_llm(user_input)
                print(f"\nAssistant: {response}")
                
                text_to_speech(response)
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        # except Exception as e:
        #     print(f"Main loop error: {str(e)}")
        #     time.sleep(1)

if __name__ == "__main__":
    main()