import streamlit as st
import utils.auth_functions as auth_functions
import utils.db_util as db_util
import utils.streamlit_utils as st_util

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
if "db" not in st.session_state:
    st.session_state.db = firestore.client()
if "model" not in st.session_state:
    st.session_state.model = None

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
    # Title
    st.title("AI Tutor")
    
    user_id = st.session_state.user.uid
    
    st.sidebar.button(label='Sign Out',on_click=auth_functions.sign_out,type='primary')
    if st.sidebar.button(f'Begin new conversation'):
        st_util.restart_conversation()
        
    st.sidebar.title("Previous Chat Sessions")
    session_ids = db_util.load_previous_sessions(user_id)
    for session in session_ids:
        if st.sidebar.button(f"Session {session['start_time']}"):
            st_util.restart_conversation(selected_session=session["session_id"])
    
    if st.session_state.selected_session:
        # Display selected chat session messages
        st.write(f"Chat History for Session {st.session_state.selected_session}")
        messages = db_util.load_chat_history(user_id, st.session_state.selected_session)
        st_util.display_chat(messages)
        if st.button(label='Delete conversation'):
            db_util.delete_chat_history(user_id, st.session_state.selected_session)
            st_util.restart_conversation()

    else:
        if audio_bytes := audio_recorder(icon_size="4x", pause_threshold=7):
            # If mic button clicked for the first time, begin conversation. 
            if not st.session_state.conversation_active:
                st.session_state.conversation_active = True
                st.session_state.session_id = str(uuid.uuid4())
                # Chatbot model response
                st.session_state.model = Model(
                    system_prompt=(
                        """
                        Play the role of a French language tutor. As a native French speaker, you will be speaking with someone who wants to improve their French skills through a simulated conversation. Imagine you met someone at a social event in France, and you don't know anything about them. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation. 
                        Additionally, develop a response generation strategy for introducing subtle corrections to your answers when the provided information is unclear or incorrect.
                        Memorize any mistakes made during the conversation and provide a comprehensive report of errors at the conclusion of the discussion, detailing the corrections and explanations for the corrections. Go!

                        NOTES:
                        - Do not wait for the user to start speaking. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation. 
                        - You should output your response in this format: <response> | <list of errors and their corrections>.
                        - Write as you would speak. Be conversational and informal.
                        - Provide concise responses, and adapt your tone and language to the level of the person you're speaking with.
                        - You should not ask more than 2 questions on the same topic.
                        - You should be engaging in the conversation by saying your opinion (do not do this every time you answer. Spice it up!).
                        - You should be engaging in the conversation by telling anecdotes that happened to you (do not do this every time you answer. Spice it up!).
                        - Ignore character errors such as using 'c' instead of 'ç' or oe instead of œ.
                        """
                    )
                )
            st_util.display_chat(st.session_state.chat_history)
            # Ensure the audio processing happens only once
            if not st.session_state.audio_processed:
                # Process the audio to text
                st.markdown("Processing audio...")
                if not TEST_MODE:
                    text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav', lang='fr')
                    message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
                else:
                    text = 'Sample text input.'
                    message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
                db_util.save_message(user_id, st.session_state.session_id, message)
                st.session_state.chat_history.append(message)
                st.session_state.audio_processed = True  # Set flag to True after processing
                st.session_state.audio_text = text  # Store the processed text in session state
                st.rerun()

            # Step 2: Send the text to chatbot model
            if "audio_text" in st.session_state and st.session_state.audio_processed and not st.session_state.text_sent:
                if not TEST_MODE:
                    response, errors = st.session_state.model.process(st.session_state.audio_text)
                else:
                    response = 'Bonjour, comment allez-vous? Voulez-vous apprendre le français?'
                    errors = ''
                st.session_state.text_sent = True  # Set flag to True after response is generated
                # Step 3: Convert the chatbot's response to speech and play
                st.markdown("Playing response...")
                audio = output_audio_gtts(response, 'fr')
                message = {"user": "assistant", "text": response, "audio_bytes": audio} 
                db_util.save_message(user_id, st.session_state.session_id, message)
                st.session_state.chat_history.append(message)
                st.session_state.chat_history.append(
                    {"user": "assistant", "text": "Errors identified: " + errors, "audio_bytes": None}
                )
                st.rerun()

        if st.session_state.conversation_active and st.session_state.text_sent:
            # Reset flags for new audio input
            st.session_state.text_sent = False
            st.session_state.audio_processed = False
