import io

import uuid
from elevenlabs import VoiceSettings
import elevenlabs.client as ec
from elevenlabs.client import ElevenLabs
from gtts import gTTS
import streamlit as st

ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]

if not ELEVENLABS_API_KEY:
    raise ValueError("ELEVENLABS_API_KEY environment variable not set")

client = ElevenLabs(
    api_key=ELEVENLABS_API_KEY,
)

def output_audio(text: str, lang: str = 'fr', stream: bool = False) -> str:
    """
    Converts text to speech and saves the output as an MP3 file.

    This function uses a specific client for text-to-speech conversion. It configures
    various parameters for the voice output and saves the resulting audio stream to an
    MP3 file with a unique name.

    Args:
        text (str): The text content to convert to speech.
        stream (bool): If True, the audio stream is returned as a generator. If not, return a file path.

    Returns:
        The file path where the audio file has been saved if stream is False, else return a generator.
    """
    # Calling the text_to_speech conversion API with detailed parameters
    response = client.text_to_speech.convert(
        voice_id="XB0fDUnXU5powFXDhCwa",  # Charlotte pre-made voice
        optimize_streaming_latency="0",
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",  # use the turbo model for low latency, for other languages use the `eleven_multilingual_v2`
        voice_settings=VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True,
        ),
    )

    if stream:
        audio_stream = io.BytesIO()

        for chunk in response:
            if chunk:
                audio_stream.write(chunk)

        audio_stream.seek(0)
        return audio_stream

    # Generating a unique file name for the output MP3 file
    save_file_path = f"{uuid.uuid4()}.mp3"

    with open(save_file_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)

    print(f"A new audio file was saved successfully at {save_file_path}")

    # Return the path of the saved audio file
    return save_file_path

def output_audio_elevenlabs(text: str, prev=ec.OMIT, next=ec.OMIT, male: bool = False):
    if not prev: prev = ec.OMIT
    if not next: next = ec.OMIT
    # Calling the text_to_speech conversion API with detailed parameters
    response = client.text_to_speech.convert(
        voice_id="nPczCjzI2devNBz1zQrb" if male else "XB0fDUnXU5powFXDhCwa",  # Charlotte/Brian pre-made voices
        optimize_streaming_latency="0",
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2",  # use the turbo model for low latency, for other languages use the `eleven_multilingual_v2`
        voice_settings=VoiceSettings(
            stability=0.1,
            similarity_boost=0.3,
            style=0.2,
            use_speaker_boost=True,
        ),
        previous_text=prev,
        next_text=next,
    )

    audio_stream = io.BytesIO()

    for chunk in response:
        if chunk:
            audio_stream.write(chunk)

    audio_stream.seek(0)
    return audio_stream


def output_audio_gtts(text: str, lang: str = 'fr'):
    tts = gTTS(text, lang=lang)
    audio_bytes = io.BytesIO()
    tts.write_to_fp(audio_bytes)
    return audio_bytes

if __name__ == "__main__":
    output_audio("Bonjour, comment allez vous? Voulez-vous apprendre le français?", lang="fr")
