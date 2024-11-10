
import streamlit as st
import os
import io
import base64  # Import base64 for encoding audio bytes

from transcribe import process_speech_to_text, process_speech_bytes_to_text
from tts import output_audio_gtts
from dialogue import Model
from pydub import AudioSegment
from audio_recorder_streamlit import audio_recorder

from dotenv import load_dotenv

load_dotenv()

TEST_MODE = False

# Initialize session state for chat history and flags
if "messages" not in st.session_state:
    st.session_state.messages = []

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
if "conversation_finished" not in st.session_state:
    st.session_state.conversation_finished = False

# Function to display chat messages in bubbles
def display_chat():
    for message in st.session_state.chat_history:
        display_message(message)

def display_message(message):
    with st.chat_message(message["user"]):
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
            if 'audio_bytes' in message and message['audio_bytes']:
                # Check if audio_bytes is a BytesIO object and extract bytes
                if isinstance(message['audio_bytes'], io.BytesIO):
                    audio_bytes = message['audio_bytes'].getvalue()
                else:
                    audio_bytes = message['audio_bytes']
                # Encode audio bytes to base64
                audio_base64 = base64.b64encode(audio_bytes).decode()
                # Create HTML audio tag with autoplay
                audio_html = f'''
                <audio controls autoplay>
                    <source src="data:audio/wav;base64,{audio_base64}" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
                '''
                st.markdown(audio_html, unsafe_allow_html=True)

# Function to analyze conversation
def analyze_conversation(chat_history):
    # Combine all user and assistant messages
    conversation = "\n".join([msg['text'] for msg in chat_history])
    
    # Initialize the model for analysis
    analysis_model = Model()
    analysis_prompt = (
        "Analyze the following conversation and provide:\n"
        "1. A summary of the conversation along with praise.\n"
        "2. Corrections for any grammar mistakes.\n"
        "3. Suggestions for improvement.\n\n"
        f"Conversation:\n{conversation}"
    )
    analysis_response, _ = analysis_model.process(analysis_prompt)
    return analysis_response

# Title
st.title("AI Tutor")

# Initialize chatbot model
model = Model()
model.process(
    "You are a system that engages in conversations with the user to help them learn French. "
    "You start by asking in English what kind of roleplay you are going to do. Then you start the roleplay in French. "
    "If the user asks you to speak in English, you do so. Otherwise, try to use simpler words if the user struggles with the language. "
    "You are a helpful assistant. You should output your response in this format: <response> | <list of errors and their corrections>."
)

# Main Conversation Logic
if st.session_state.conversation_active and not st.session_state.conversation_finished:
    display_chat()
    audio_bytes = audio_recorder(icon_size="4x", pause_threshold=7)
    if audio_bytes:
        # Ensure the audio processing happens only once
        if not st.session_state.audio_processed:
            # Process the audio to text
            st.markdown("Processing audio...")
            if not TEST_MODE:
                text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav', lang='fr')
                message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
            else:
                text = 'Sample text'
                message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
            st.session_state.chat_history.append(message)
            st.session_state.audio_processed = True  # Set flag to True after processing
            st.session_state.audio_text = text  # Store the processed text in session state
            st.experimental_rerun()

        # Step 2: Send the text to chatbot model
        if "audio_text" in st.session_state and st.session_state.audio_processed and not st.session_state.text_sent:
            if not TEST_MODE:
                response, errors = model.process(st.session_state.audio_text)
            else:
                response = 'Bonjour, comment allez-vous? Voulez-vous apprendre le français?'
                errors = ''
            st.session_state.text_sent = True  # Set flag to True after response is generated
            # Step 3: Convert the chatbot's response to speech and play
            st.markdown("Playing response...")
            audio = output_audio_gtts(response, 'fr')
            message = {"user": "assistant", "text": response, "audio_bytes": audio}
            st.session_state.chat_history.append(message)
            if errors:
                st.session_state.chat_history.append({"user": "assistant", "text": "Errors identified: " + errors, "audio_bytes": None})
            st.experimental_rerun()

    if st.session_state.text_sent:
        # Reset flags for new audio input
        st.session_state.text_sent = False
        st.session_state.audio_processed = False

    # Finish Conversation Button (Properly Indented)
    if st.button("Finish Conversation"):
        st.session_state.conversation_finished = True
        st.session_state.conversation_active = False
        st.experimental_rerun()

# If conversation is finished, display feedback along with chat history
if st.session_state.conversation_finished:
    st.header("Conversation Analysis")
    analysis = analyze_conversation(st.session_state.chat_history)
    st.write(analysis)
    
    st.header("Chat History")
    display_chat()

    # Optionally, allow the user to restart the conversation
    if st.button("Restart Conversation"):
        st.session_state.chat_history = []
        st.session_state.conversation_active = True
        st.session_state.conversation_finished = False
        st.experimental_rerun()