
import soundfile as sf
from espnet2.bin.tts_inference import Text2Speech
import os
from espnet_model_zoo.downloader import ModelDownloader


d = ModelDownloader()  # <module_dir> is used as cachedir by default
model = d.download_and_unpack("https://zenodo.org/record/3986231/files/tts_train_fastspeech_raw_phn_tacotron_g2p_en_no_space_train.loss.best.zip?download=1")


def text_to_speech(text):
    # Load the pre-trained TTS model
    text2speech = Text2Speech.from_pretrained("model")

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
