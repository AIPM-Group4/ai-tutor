import streamlit as st
import os
import io

from transcribe_api import process_speech_to_text, process_speech_bytes_to_text
from tts_api import output_audio
from dialogue_api import Model
from pydub import AudioSegment
from audio_recorder_streamlit import audio_recorder

from dotenv import load_dotenv

load_dotenv()

TEST_MODE = True

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
        
# Initialize session state for chat history and flags
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "audio_processed" not in st.session_state:
    st.session_state.audio_processed = False
if "text_sent" not in st.session_state:
    st.session_state.text_sent = False
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = True
if "audio_bytes" not in st.session_state:
    st.session_state.audio_bytes = None

# Function to display chat messages in bubbles
def display_chat():
    for message in st.session_state.chat_history:
        display_message(message)

def display_message(message):
    with st.chat_message("user"):
        if message["user"] == "user":
            st.markdown(
                f"<div style='text-align: right; background-color: #d1e7ff; color: black; padding: 10px; border-radius: 10px; margin: 10px 0; width: fit-content; float: right;'>{message['text']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='text-align: left; background-color: #f0f0f0; color: black; padding: 10px; border-radius: 10px; margin: 10px 0; width: fit-content; float: left;'>{message['text']}</div>",
                unsafe_allow_html=True,
            )
        if 'audio_bytes' in message and message['audio_bytes']: # If statement for prod/test mode
            st.audio(message['audio_bytes'], format="audio/wav")

# Title
st.title("AI Tutor")

if st.session_state.conversation_active:
    display_chat()
    if audio_bytes := audio_recorder(icon_size="1x"):
        # Ensure the audio processing happens only once
        if not st.session_state.audio_processed:
            # Process the audio to text
            st.markdown("Processing audio...")
            if not TEST_MODE:
                text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav')
                message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
            else:
                text = 'text'
                message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
            st.session_state.chat_history.append(message)
            st.session_state.audio_processed = True  # Set flag to True after processing
            st.session_state.audio_text = text  # Store the processed text in session state
            st.rerun()

        # Step 2: Send the text to chatbot model
        if "audio_text" in st.session_state and st.session_state.audio_processed and not st.session_state.text_sent:
            # Chatbot model response
            model = Model()
            if not TEST_MODE:
                response = model.process(st.session_state.audio_text)
            else:
                response = 'response'
            st.session_state.text_sent = True  # Set flag to True after response is generated
            # Step 3: Convert the chatbot's response to speech and play
            st.markdown("Playing response...")
            if not TEST_MODE:
                message = {"user": "assistant", "text": response, "audio_bytes": output_audio(response, stream=True)}
            else:
                message = {"user": "assistant", "text": response, "audio_bytes": None}
            st.session_state.chat_history.append(message)
            st.rerun()

if st.session_state.conversation_active and st.session_state.text_sent:
    # Reset flags for new audio input
    st.session_state.text_sent = False
    st.session_state.audio_processed = False

#if st.button("Finish conversation"):
    #st.session_state.conversation_active = False  # Keep the conversation active
    #st.session_state.text_sent = True
    #st.session_state.audio_processed = True