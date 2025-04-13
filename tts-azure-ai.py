import requests
import json

# Azure TTS Configuration - REPLACE THESE WITH YOUR VALUES
API_KEY = "G0J4tRTyRqeHABXNW1dnA6t5D3FZOpzKz3wj39RYZsqP1yuFel6UJQQJ99BCACfhMk5XJ3w3AAAAACOGrroB"
REGION = "swedencentral"  # e.g. "eastus"
ENDPOINT = f"https://{REGION}.tts.speech.microsoft.com/cognitiveservices/v1"

# Text to synthesize
text_to_synthesize = "Hello, this is a text-to-speech test using Azure AI. Yo yo yo whats up!"

# Request headers
headers = {
    "Ocp-Apim-Subscription-Key": API_KEY,
    "Content-Type": "application/ssml+xml",
    "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
    "User-Agent": "python-tts-app"
}

# SSML payload - modify voice name as needed
ssml_payload = f"""
<speak version='1.0' xml:lang='en-US'>
    <voice name='en-US-JennyNeural'>
        {text_to_synthesize}
    </voice>
</speak>
"""

try:
    # Make the API call
    response = requests.post(
        ENDPOINT,
        headers=headers,
        data=ssml_payload.encode('utf-8')
    )

    # Check response status
    if response.status_code == 200:
        # Save the audio file
        with open("output_audio.mp3", "wb") as audio_file:
            audio_file.write(response.content)
        print("Audio file saved successfully!")
    else:
        print(f"Error: {response.status_code} - {response.text}")

except Exception as e:
    print(f"Exception occurred: {str(e)}")