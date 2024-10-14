from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def process_speech_to_text(audio_file_path, lang="en"):
    audio_file = open(audio_file_path, "rb")
    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text",
        language=lang,
    )
    return transcript

print(process_speech_to_text("New Recording 37.m4a"))
