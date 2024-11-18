from mutagen.mp3 import MP3
import io
import time
from tts import output_audio_gtts
import queue
import streamlit as st
import threading

# Function to display chat messages in bubbles
def display_chat(messages):
    for message in messages:
        display_message(message)

def restart_conversation(text_sent=False, audio_processed=False, chat_history=[], conversation_active=False, selected_session=None):
    st.session_state.text_sent = text_sent
    st.session_state.audio_processed = audio_processed
    st.session_state.chat_history = chat_history
    st.session_state.conversation_active = conversation_active
    st.session_state.selected_session = selected_session
    st.session_state.model = None
    st.rerun()
    
def display_message(message):
    with st.chat_message(message["user"]):
        if message["user"] == "user":
            st.markdown(
                f"<div style='text-align: right; background-color: #d1e7ff; color: black; padding: 10px; "
                f"border-radius: 10px; margin: 10px 0; width: fit-content; float: right;'>{message['text']}</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='text-align: left; background-color: #f0f0f0; color: black; padding: 10px; "
                f"border-radius: 10px; margin: 10px 0; width: fit-content; float: left;'>{message['text']}</div>",
                unsafe_allow_html=True,
            )
            if 'audio_bytes' in message and message['audio_bytes']:
                st.audio(message['audio_bytes'], format="audio/wav", autoplay=True)

SENTINEL = "FINISHED"

def _streaming_worker(text, q):
    audio = bytearray()
    chunks = text.split('.')
    for chunk in chunks:
        chunk_audio = output_audio_gtts(chunk, 'fr')
        q.put(chunk_audio)
        # Calculate duration
        aux = MP3(chunk_audio)
        duration = aux.info.length
        q.put(duration)
        audio.extend(chunk_audio.getvalue())
    q.put(SENTINEL)
    return io.BytesIO(audio)


def stream_tts(text):
    q = queue.Queue()
    t = threading.Thread(target=_streaming_worker, args=(text, q))
    t.start()
    audio_placeholder = st.empty()
    text_placeholder = st.empty()
    chunks = text.split('.')
    current_text = ""
    previous_text = ""
    chunk_idx = 0
    chunk_audio = q.get()
    while chunk_audio != SENTINEL:
        if chunk_idx < len(chunks):
            previous_text = current_text
            current_text += chunks[chunk_idx] + "."
            text_placeholder.markdown(f"{previous_text} **{chunks[chunk_idx].strip()}.**")
            chunk_idx += 1
        audio_placeholder.audio(chunk_audio, format="audio/wav", autoplay=True)
        duration = q.get()
        time.sleep(duration)
        chunk_audio = q.get()

    audio = t.join()
    return audio
