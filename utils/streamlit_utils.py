from mutagen.mp3 import MP3
import io
import time
from tts import output_audio_elevenlabs, output_audio_gtts
import queue
import re
import streamlit as st
from . import db_util
import threading
from openai import OpenAI

# Use OpenAI API for translation
client = OpenAI(api_key=st.secrets['OPENAI_API_KEY'])

# Function to display chat messages in bubbles
def display_chat(messages):
    for message in messages:
        display_message(message)
        
def display_settings(session_data):
    if not 'settings' in session_data:
        return
    settings = session_data['settings']
    # For scenario text prompt
    if len(settings) > 0:
        st.subheader('Settings')
    if 'text_prompt' in settings:
        prompt = settings['text_prompt']
        st.write(f'Scenario prompt: {prompt}')
        
def display_chat_title(session_data):
    st.header(f"{session_data['title']}")
    st.write(f'Conversation started at {session_data.get("start_time"):%Y-%m-%d %H:%M:%S}.')
    col1B, col2B, col3B = st.columns([0.18, 0.4, 0.43])
    if 'renaming_title' not in st.session_state or not st.session_state.renaming_title:
        if col1B.button('Rename Title'):
            st.session_state.renaming_title = True
            st.rerun()
        if col2B.button(label='Delete conversation'):
            db_util.delete_chat_history(st.session_state.user.uid, st.session_state.selected_session)
            restart_conversation()
    else:
        new_title = st.text_input('New title: ')
        col1, col2, col3 = st.columns([0.1, 0.1, 0.7])
        if col1.button('Save'):
            if new_title:
                db_util.save_new_title(st.session_state.user.uid, st.session_state.selected_session, new_title)
                st.session_state.renaming_title = False
                st.rerun()
        if col2.button('Cancel'):
            st.session_state.renaming_title = False
            st.rerun()
    
def display_feedback(session_data):
    if "feedback" in session_data:
        st.write("## Feedback Summary")
        st.write(session_data['feedback'])

def restart_conversation(text_sent=False, 
                         audio_processed=False, 
                         chat_history=[], 
                         conversation_active=False,
                         selected_session=None,
                         session_id=None,
                         model=None,
                         renaming_title=False):
    st.session_state.text_sent = text_sent
    st.session_state.audio_processed = audio_processed
    st.session_state.chat_history = chat_history
    st.session_state.conversation_active = conversation_active
    st.session_state.selected_session = selected_session
    st.session_state.model = model
    st.session_state.renaming_title = renaming_title
    st.session_state.session_id=session_id
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
                st.audio(message['audio_bytes'], format="audio/wav", autoplay=False)

    if 'translated_text' in message and message['translated_text']:
        with st.expander("Show translation"):
            st.write(message['translated_text'])


def _streaming_worker(text, q, lang='Français'):
    full_audio = bytearray()
    full_text = ""

    chunks = re.split("(\.|\!|\?)", text)
    if chunks[-1] == "": chunks = chunks[:-1]
    chunks = [(chunks[i] + chunks[i+1]).strip() + " " for i in range(0, len(chunks), 2)]

    for chunk_text in chunks:
        # Generate audio
        l = 'fr' if lang == 'Français' else 'de'
        chunk_audio = output_audio_gtts(chunk_text, l)
        # chunk_audio = output_audio_elevenlabs(text=chunk_text, prev=full_text, lang=lang)

        # Calculate duration
        aux = MP3(chunk_audio)
        duration = aux.info.length

        # Send chunk
        q.put((chunk_audio, duration, full_text, chunk_text))

        # Extend
        full_audio.extend(chunk_audio.getvalue())
        full_text += chunk_text

    q.put(None)
    return io.BytesIO(full_audio)


def translate_text(text, target_lang='English'):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": f"Translate the following text to {target_lang}: {text}. Only output the translation, no other text."}]
    )
    return response.choices[0].message.content


def stream_tts(text, translation=True, lang='Français'):
    with st.expander("Show transcription", expanded=False):
        text_placeholder = st.empty()
    with st.expander("Show translation"):
        translation_placeholder = st.empty()
    prev_translated_text = ""
    audio_placeholder = st.empty()
    q = queue.Queue()
    full_audio = bytearray()
    t = threading.Thread(target=_streaming_worker, args=(text, q, lang))
    t.start()

    chunk = q.get()
    while chunk:
        chunk_audio, duration, prev_text, chunk_text = chunk
        text_placeholder.markdown(
            f"{prev_text} **{chunk_text.strip()}**",
        )
        audio_placeholder.audio(chunk_audio, format="audio/wav", autoplay=True)
        full_audio.extend(chunk_audio.getvalue())
        current_time = time.time()
        if translation:
            translated_text = translate_text(chunk_text, target_lang='en')
        else:
            translated_text = ""
        translation_placeholder.markdown(
            f"{prev_translated_text} **{translated_text.strip()}**",
        )
        prev_translated_text += f' {translated_text}'
        translation_time = time.time() - current_time
        # Wait for audio to finish playing
        # time.sleep(duration)
        remaining_time = duration - translation_time
        if remaining_time > 0:
            time.sleep(remaining_time)
        
        # Check if running on mobile device
        is_mobile = st.session_state.get('is_mobile', True)
        print(is_mobile)
        if is_mobile:
            time.sleep(2)
        chunk = q.get()

    t.join()
    return io.BytesIO(full_audio), prev_translated_text