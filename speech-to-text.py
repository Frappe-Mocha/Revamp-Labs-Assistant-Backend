import requests

def transcribe_audio(api_key, audio_file):
    url = "https://api.elevenlabs.io/v1/speech-to-text"
    headers = {
        "xi-api-key": api_key
    }
    files = {
        "file": open(audio_file, "rb")
    }
    data = {
        "model_id": "scribe_v1"
    }
    response = requests.post(url, headers=headers, files=files, data=data)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

# Example usage:
api_key = "sk_e93d2bb951ecd7df79ba7d3ca9f2cfb4f63ce2556c782585"
transcription = transcribe_audio(api_key, 'output.wav')
if transcription:
    print("Transcription:", transcription.get("text", "No transcription found."))
