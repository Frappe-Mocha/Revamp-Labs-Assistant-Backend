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
from playwright.sync_api import sync_playwright
import re

# ================== Configuration ==================
AZURE_SPEECH_KEY="<Azure-Speech-Key>"
AZURE_OPENAI_API_KEY="<Azure-OpenAI-Key>"
AZURE_SERVICE_REGION = "westeurope"
TTS_VOICE_NAME = "en-US-JennyNeural"
AZURE_OPENAI_ENDPOINT = "https://storegpt-ai-service-1.openai.azure.com/"

CONVERSATION_HISTORY_MAX = 6
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024

# ================== Global State ==================
conversation_history = deque(maxlen=CONVERSATION_HISTORY_MAX)
is_speaking = False
browser = None
page = None
playwright_instance = None

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

# ================== Playwright Functions ==================
def initialize_browser():
    """Initialize Playwright browser instance"""
    global browser, page, playwright_instance
    
    playwright_instance = sync_playwright().start()
    browser = playwright_instance.chromium.launch(headless=False, slow_mo=100)
    page = browser.new_page()
    page.goto("https://www.youtube.com")
    print("Browser initialized and YouTube loaded")

def close_browser():
    """Close Playwright browser instance"""
    global browser, playwright_instance
    if browser:
        browser.close()
    if playwright_instance:
        playwright_instance.stop()
    print("Browser closed")

def handle_youtube_command(command):
    """Execute YouTube commands based on voice input"""
    global page
    
    if not page:
        initialize_browser()
    
    # Normalize command
    command = command.lower().strip()
    
    # Search for videos
    if "search for" in command:
        query = re.sub(r'search for|on youtube', '', command, flags=re.IGNORECASE).strip()
        search_youtube(query)
        return f"Searching YouTube for {query}"
    
    # Play/pause control
    elif any(word in command for word in ["play", "pause", "resume"]):
        page.keyboard.press("Space")
        return "Toggled play/pause"
    
    # Volume control
    elif "volume up" in command:
        for _ in range(3):
            page.keyboard.press("ArrowUp")
        return "Increased volume"
    elif "volume down" in command:
        for _ in range(3):
            page.keyboard.press("ArrowDown")
        return "Decreased volume"
    
    # Fullscreen
    elif "fullscreen" in command:
        page.keyboard.press("f")
        return "Toggled fullscreen"
    
    # Skip forward/backward
    elif "skip forward" in command:
        page.keyboard.press("ArrowRight")
        return "Skipped forward 5 seconds"
    elif "go back" in command or "skip backward" in command:
        page.keyboard.press("ArrowLeft")
        return "Went back 5 seconds"
    
    # Mute
    elif "mute" in command:
        page.keyboard.press("m")
        return "Toggled mute"
    
    # Like/dislike
    elif "like this" in command:
        page.keyboard.press("Shift+.")
        return "Liked the video"
    elif "dislike this" in command:
        page.keyboard.press("Shift+,")
        return "Disliked the video"
    
    # Open specific video
    elif "open video" in command:
        video_title = re.sub(r'open video|on youtube', '', command, flags=re.IGNORECASE).strip()
        search_youtube(video_title)
        page.click("ytd-video-renderer:has-text('"+video_title+"') >> nth=0")
        return f"Opening video: {video_title}"
    
    # Default response if no command matched
    return "I didn't understand that YouTube command"

def search_youtube(query):
    """Search YouTube for a query"""
    global page
    
    search_box = page.get_by_placeholder("Search")
    search_box.click()
    search_box.fill("")
    search_box.fill(query)
    page.keyboard.press("Enter")
    time.sleep(2)  # Wait for results to load

# ================== Modified Core Functions ==================
def chat_with_llm(prompt):
    """Complete LLM interaction with conversation history and YouTube control"""
    global conversation_history
    
    # Check for YouTube commands first
    youtube_triggers = ["youtube", "video", "play", "pause", "search", "volume", "skip", "mute"]
    if any(trigger in prompt.lower() for trigger in youtube_triggers):
        response = handle_youtube_command(prompt)
        conversation_history.append({"role": "assistant", "content": [{"type": "text", "text": response}]})
        return response
    
    # Normal conversation
    system_message = {
        "role": "system",
        "content": [{
            "type": "text", 
            "text": """You're a conversational assistant with YouTube control capabilities. 
            For YouTube commands, respond concisely with the action taken.
            For normal conversation, respond naturally (1-2 sentences)."""
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


# ================== Main Loop ==================
def main():
    print("Voice Assistant Ready - Speak Naturally!")
    
    try:
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
    finally:
        close_browser()

if __name__ == "__main__":
    main()