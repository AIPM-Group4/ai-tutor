import streamlit as st
import os

from audio_processing import process_speech_to_text
from text_to_speech import output_audio
from dialogue import Model

# Initialize session state for chat history and flags
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "audio_processed" not in st.session_state:
    st.session_state.audio_processed = False
if "text_sent" not in st.session_state:
    st.session_state.text_sent = False

# Function to display chat messages in bubbles
def display_chat():
    for message in st.session_state.chat_history:
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
    # Clear floating elements after chat bubbles
    st.markdown("<div style='clear: both;'></div>", unsafe_allow_html=True)

# Title
st.title("AI Tutor")

# Display chat bubbles
display_chat()

# Step 1: Upload an audio file
uploaded_file = st.file_uploader("Upload an audio file", type=["wav", "mp3", "m4a"])

if uploaded_file is not None:
    # Ensure the audio processing happens only once
    if not st.session_state.audio_processed:
        st.session_state.chat_history.append({"user": "user", "text": "Voice file uploaded."})
        st.audio(uploaded_file, format="audio/wav")

        # Process the uploaded audio file to text
        try:
            st.markdown("Processing audio file...")
            text = process_speech_to_text(uploaded_file)
            st.session_state.chat_history.append({"user": "user", "text": text})
            st.session_state.audio_processed = True  # Set flag to True after processing
            st.session_state.audio_text = text  # Store the processed text in session state
            display_chat()
        except Exception as e:
            st.error(f"Error processing the audio file: {e}")
            st.session_state.chat_history.append({"user": "ai", "text": "Failed to process the audio file."})

# Step 2: Send the text to chatbot model
if "audio_text" in st.session_state and st.session_state.audio_processed and not st.session_state.text_sent:
    if st.button("Send"):
        st.session_state.chat_history.append({"user": "user", "text": "Processing..."})
        display_chat()

        # Chatbot model response
        model = Model()
        response = model.process(st.session_state.audio_text)
        st.session_state.chat_history.append({"user": "ai", "text": response})
        st.session_state.text_sent = True  # Set flag to True after response is generated
        display_chat()

        # Step 3: Convert the chatbot's response to speech and play
        st.markdown("Playing response...")
        output_audio(response)
