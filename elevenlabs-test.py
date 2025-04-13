from elevenlabs import ElevenLabs, stream

# Initialize the ElevenLabs client with your API key
client = ElevenLabs(api_key="sk_e93d2bb951ecd7df79ba7d3ca9f2cfb4f63ce2556c782585")

# Define the text you want to synthesize
text_to_speak = "hey there! I'm your new assistant to help you with the product demo of Hubilo. Let me take you to the demo page."

# Generate the audio stream
audio_stream = client.text_to_speech.convert_as_stream(
    voice_id="iP95p4xoKVk53GoZ742B",  # Replace with your desired voice ID
    output_format="mp3_44100_128",
    text=text_to_speak,
    model_id="eleven_multilingual_v2"
)

# Play the streamed audio locally
stream(audio_stream)