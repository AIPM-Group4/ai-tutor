
import soundfile as sf
from espnet2.bin.tts_inference import Text2Speech
import os
from espnet_model_zoo.downloader import ModelDownloader
import shutil
from huggingface_hub import hf_hub_download
from pathlib import Path
import nltk


nltk.download('averaged_perceptron_tagger_eng')


def text_to_speech(text):
    # Load the pre-trained TTS model
    text2speech = Text2Speech.from_pretrained(model_tag="kan-bayashi/ljspeech_tacotron2")

    # Perform text-to-speech
    speech = text2speech(text)["wav"]

    # Ensure the "Audio" directory exists
    os.makedirs("Audio", exist_ok=True)

    # Save the audio file in the "Audio" directory
    output_path = os.path.join("Audio", "output.wav")

    # Save the output to a WAV file in the "Audio" folder
    sf.write(output_path , speech.numpy(), text2speech.fs, "PCM_16")







# Test the function
text = "Hello, this is a test of the text-to-speech function."
text_to_speech(text)
