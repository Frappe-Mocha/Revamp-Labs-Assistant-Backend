import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wavfile

def record_audio(duration, filename, sample_rate=44100):
    print("Recording...")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished.")
    wavfile.write(filename, sample_rate, audio_data)
    return filename

# Example usage:
audio_file = record_audio(duration=5, filename='output.wav')
