import azure.cognitiveservices.speech as speechsdk
import sounddevice as sd
import soundfile as sf
import time

# ================== Azure Configuration ==================
AZURE_SPEECH_KEY = "Azure-Speech-Key"  # Replace with your Azure Speech Service key
AZURE_SERVICE_REGION = "westeurope"  # e.g., "eastus"
AZURE_ENDPOINT = "https://westeurope.api.cognitive.microsoft.com/"  # Optional if using standard endpoints

# ================== Audio Recording Parameters ==================
SAMPLE_RATE = 16000  # Sample rate for recording
CHANNELS = 1         # Mono audio
DURATION = 5         # Recording duration in seconds
FILENAME = "recorded_audio.wav"

# ================== Record Audio ==================
def record_audio():
    print("Recording... (Speak now)")
    audio_data = sd.rec(
        int(SAMPLE_RATE * DURATION),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype='int16'
    )
    sd.wait()  # Wait until recording is finished
    sf.write(FILENAME, audio_data, SAMPLE_RATE)
    print(f"Audio saved as {FILENAME}")
    return FILENAME

# ================== Speech-to-Text ==================
def speech_to_text(audio_file):
    # Configure Azure Speech Service
    # speech_config = speechsdk.SpeechConfig(
    #     subscription=AZURE_SPEECH_KEY,
    #     region=AZURE_SERVICE_REGION,
    #     endpoint=AZURE_ENDPOINT  # Can be omitted if using standard region-based endpoint
    # )

    # Use this if your endpoint follows the regional format:
    # "https://<REGION>.api.cognitive.microsoft.com"
    speech_config = speechsdk.SpeechConfig(
        subscription=AZURE_SPEECH_KEY,
        region=AZURE_SERVICE_REGION  # <--- ONLY region
    )
    
    # Configure audio input
    audio_input = speechsdk.audio.AudioConfig(filename=audio_file)
    
    # Create speech recognizer
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config,
        audio_config=audio_input
    )
    
    # Perform recognition
    result = speech_recognizer.recognize_once()
    
    # Handle results
    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"Recognized: {result.text}")
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("No speech could be recognized")
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print(f"Recognition canceled: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print(f"Error details: {cancellation_details.error_details}")

# ================== Main Execution ==================
if __name__ == "__main__":
    # 1. Record audio from microphone
    audio_file = record_audio()
    
    # 2. Convert to text using Azure
    speech_to_text(audio_file)