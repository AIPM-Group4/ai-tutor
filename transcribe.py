from openai import OpenAI
import streamlit as st

load_dotenv()

client = OpenAI(
    api_key=st.secrets['OPENAI_API_KEY']
)

def process_speech_to_text(audio_file, lang="en"):
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text",
        language=lang,
    )
    return transcript

def process_speech_bytes_to_text(file_type, file_bytes, content_type, lang="en"):
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=("temp." + file_type, file_bytes, content_type),
        response_format="text",
        language=lang,
    )
    return transcript
# print(process_speech_to_text("New Recording 37.m4a"))
