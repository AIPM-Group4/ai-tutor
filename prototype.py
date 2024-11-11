import streamlit as st
import utils.auth_functions as auth_functions

from transcribe import process_speech_to_text, process_speech_bytes_to_text
from tts import output_audio_gtts
from dialogue import Model
import firebase_admin
from firebase_admin import firestore, initialize_app, credentials
import datetime
from audio_recorder_streamlit import audio_recorder
import uuid
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = False

if not firebase_admin._apps: 
    cred = credentials.Certificate(dict(st.secrets['FIREBASE_CRED']['cred']))
    initialize_app(cred)
        
# Initialize session state for chat history and flags
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "audio_processed" not in st.session_state:
    st.session_state.audio_processed = False
if "text_sent" not in st.session_state:
    st.session_state.text_sent = False
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

db = firestore.client()

# If not logged in.
if st.session_state.user == None:
    col1,col2,col3 = st.columns([1,2,1])

    # Authentication form layout
    do_you_have_an_account = col2.selectbox(label='Do you have an account?',options=('Yes','No','I forgot my password'))
    auth_form = col2.form(key='Authentication form',clear_on_submit=False)
    email = auth_form.text_input(label='Email')
    password = auth_form.text_input(label='Password',type='password') if do_you_have_an_account in {'Yes','No'} else auth_form.empty()
    auth_notification = col2.empty()

    # Sign In
    if do_you_have_an_account == 'Yes' and auth_form.form_submit_button(label='Sign In',use_container_width=True,type='primary'):
        with auth_notification, st.spinner('Signing in'):
            auth_functions.sign_in(email,password)

    # Create Account
    elif do_you_have_an_account == 'No' and auth_form.form_submit_button(label='Create Account',use_container_width=True,type='primary'):
        with auth_notification, st.spinner('Creating account'):
            auth_functions.create_account(email,password)

    # Password Reset
    elif do_you_have_an_account == 'I forgot my password' and auth_form.form_submit_button(label='Send Password Reset Email',use_container_width=True,type='primary'):
        with auth_notification, st.spinner('Sending password reset link'):
            auth_functions.reset_password(email)

    # Authentication success and warning messages
    if 'auth_success' in st.session_state:
        auth_notification.success(st.session_state.auth_success)
        del st.session_state.auth_success
    elif 'auth_warning' in st.session_state:
        auth_notification.warning(st.session_state.auth_warning)
        del st.session_state.auth_warning

# If logged in
else:
    def save_message(user_id, session_id, message):
        session_ref = db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
        if not session_ref.get().exists:
            session_ref.set({
                "start_time": datetime.datetime.now(),
                "messages": []
            })
        message = dict(message)
        message["audio_bytes"] = None # Firestore can't handle bytes
        # Add message to messages array
        session_ref.update({
            "messages": firestore.ArrayUnion([message])
        })

    def load_previous_sessions(user_id):
        sessions_ref = db.collection("students").document(user_id).collection("chat_sessions")
        sessions = sessions_ref.stream()
        
        session_ids = []
        for session in sessions:
            session_data = session.to_dict()
            session_ids.append({
                "session_id": session.id,
                "start_time": session_data.get("start_time")
            })
        return session_ids
    
    def load_chat_history(user_id, session_id):
        session_ref = db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
        session_data = session_ref.get().to_dict()
        return session_data['messages']
    
    def delete_chat_history(user_id, session_id):
        db.collection("students").document(user_id).collection("chat_sessions").document(session_id).delete()

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
        st.rerun()

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
                if message['audio_bytes']:
                    st.audio(message['audio_bytes'], format="audio/wav", autoplay=True)
    # Title
    st.title("AI Tutor")
    
    user_id = st.session_state.user.uid
    
    st.sidebar.button(label='Sign Out',on_click=auth_functions.sign_out,type='primary')
    if st.sidebar.button(f'Begin new conversation'):
        restart_conversation()
        
    st.sidebar.title("Previous Chat Sessions")
    session_ids = load_previous_sessions(user_id)
    for session in session_ids:
        if st.sidebar.button(f"Session {session['session_id']} - {session['start_time']}"):
            restart_conversation(selected_session=session["session_id"])
    
    if st.session_state.selected_session:
        # Display selected chat session messages
        st.write(f"Chat History for Session {st.session_state.selected_session}")
        messages = load_chat_history(user_id, st.session_state.selected_session)
        display_chat(messages)
        if st.button(label='Delete conversation'):
            delete_chat_history(user_id, st.session_state.selected_session)
            restart_conversation()

    else:
        if audio_bytes := audio_recorder(icon_size="4x", pause_threshold=7):
            if not st.session_state.conversation_active:
                st.session_state.conversation_active = True
                st.session_state.session_id = str(uuid.uuid4())
                # Chatbot model response
                st.session_state.model = Model()
                st.session_state.model.process("You are a system that engages in conversations with the user to help them learn french. You start by asking in English what kind of roleplay you are going to do. Then you start the roleplay in french. If the user asks you to speak in English, you do so. Otherwise, try to use simpler words if the user struggles with the language. You are a helpful assistant. You should output you response in this format: <response> | <list of errors and their corrections>.")
            display_chat(st.session_state.chat_history)
            model = st.session_state.model
            # Ensure the audio processing happens only once
            if not st.session_state.audio_processed:
                # Process the audio to text
                st.markdown("Processing audio...")
                if not TEST_MODE:
                    text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav', lang='fr')
                    message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
                else:
                    text = 'text'
                    message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
                save_message(user_id, st.session_state.session_id, message)
                st.session_state.chat_history.append(message)
                st.session_state.audio_processed = True  # Set flag to True after processing
                st.session_state.audio_text = text  # Store the processed text in session state
                st.rerun()

            # Step 2: Send the text to chatbot model
            if "audio_text" in st.session_state and st.session_state.audio_processed and not st.session_state.text_sent:
                if not TEST_MODE:
                    response, errors = model.process(st.session_state.audio_text)
                else:
                    response = 'Bonjour, comment allez vous? Voulez-vous apprendre le français?'
                    errors = ''
                st.session_state.text_sent = True  # Set flag to True after response is generated
                # Step 3: Convert the chatbot's response to speech and play
                st.markdown("Playing response...")
                audio = output_audio_gtts(response, 'fr')
                #audio = output_audio(response, stream=True)
                message = {"user": "assistant", "text": response, "audio_bytes": audio} 
                save_message(user_id, st.session_state.session_id, message)
                st.session_state.chat_history.append(message)
                st.session_state.chat_history.append({"user": "assistant", "text": "Errors identified: " + errors, "audio_bytes": None})
                st.rerun()

        if st.session_state.conversation_active and st.session_state.text_sent:
            # Reset flags for new audio input
            st.session_state.text_sent = False
            st.session_state.audio_processed = False

        #if st.button("Finish conversation"):
            #st.session_state.conversation_active = False  # Keep the conversation active
            #st.session_state.text_sent = True
            #st.session_state.audio_processed = True