import streamlit as st
import os
import sys
sys.path.append(os.path.join(os.getcwd(), "ai-tutor"))
import gtts
from gtts import gTTS
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
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False

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

# 音声ファイルを生成する関数
def output_audio(text, filename="output.mp3"):
    tts = gTTS(text)
    tts.save(filename)
    print(f"Audio file saved as: {filename}")

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
        # show the response text in the chat
        st.session_state.text_sent = True  # Set flag to True after response is generated
        display_chat()

        # Step 3: Convert the chatbot's response to speech and play
        st.markdown("Playing response...")
        output_audio(response)

        # Check if output.mp3 was successfully created
        output_path = os.path.join(os.getcwd(), "output.mp3")
        if os.path.exists(output_path):
            st.audio(output_path, format="audio/mp3")
            st.session_state.chat_history.append({"user": "ai", "text": "Playing response..."})
        else:
            st.error("Error: Audio file not found. Could not play the response.")

# conversation continues
if st.session_state.text_sent:
    if st.button("Continue conversation"):
        # Reset flags for new audio input
        st.session_state.text_sent = False
        st.session_state.audio_processed = False
        st.session_state.conversation_active = True  # Keep the conversation active
        st.write("Upload a new audio file to continue the conversation.")
    else:
        st.write("Conversation ended. Upload a new audio file to start a new conversation.")
