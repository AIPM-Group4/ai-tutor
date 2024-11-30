import streamlit as st
import utils.auth_functions as auth_functions
import utils.db_util as db_util
import utils.streamlit_utils as st_util
from firebase_admin import auth

from transcribe import process_speech_to_text, process_speech_bytes_to_text
from dialogue import Model
import firebase_admin
from firebase_admin import firestore, initialize_app, credentials
import datetime
from utils.streamlit_google_auth import Authenticate
from audio_recorder_streamlit import audio_recorder
import uuid
from dotenv import load_dotenv

load_dotenv()

TEST_MODE = False

if not firebase_admin._apps: 
    cred = credentials.Certificate(dict(st.secrets['CRED']['firebase_cred']))
    initialize_app(cred)
       
        
def generate_feedback(chat_history):
    """
    Generate feedback for the conversation session.
    """
    summary = " ".join([msg['text'] for msg in chat_history if msg['user'] == "user"])
    compliments = "Great job on your engagement and effort!"
    grammatical_feedback = "Focus on verb conjugations and agreement in adjectives."
    suggestions = "Practice advanced tenses and idiomatic expressions."

    feedback = {
        "summary": summary,
        "compliments": compliments,
        "grammatical_feedback": grammatical_feedback,
        "suggestions": suggestions,
    }
    return feedback

# Initialize session state for chat history and flags
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "audio_processed" not in st.session_state:
    st.session_state.audio_processed = False
if "text_sent" not in st.session_state:
    st.session_state.text_sent = False
if "conversation_active" not in st.session_state:
    st.session_state.conversation_active = False
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None # For Previous Session selection
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "db" not in st.session_state:
    st.session_state.db = firestore.client()
if "model" not in st.session_state:
    st.session_state.model = None
if "authenticator" not in st.session_state:
    st.session_state.authenticator = Authenticate(
        secret_credentials_config = dict(st.secrets['CRED']['oauth_cred']),
        cookie_name='my_cookie_name',
        cookie_key='this_is_secret',
        redirect_uri = 'http://localhost:8501',
    )

# If not logged in.
if not st.session_state.user_info or "authorized" not in st.session_state or not st.session_state.authorized:
    col1,col2,col3 = st.columns([1,2,1])
    auth_functions.google_auth()

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
    if 'oauth_id' in st.session_state and st.session_state['oauth_id']:
        user_id = st.session_state.oauth_id
    else:
        # If account created by email
        email = st.session_state.user_info["email"]
        user = auth.get_user_by_email(email)
        user_id = user.uid
        
    st.markdown('''
    <style>
        [data-testid="stSidebar"]{
            min-width: 367px;
            max-width: 400px;
        }
    </style>
    ''', unsafe_allow_html=True)
    col1, col2, col3 = st.sidebar.columns(([2, 1, 0.2]))
    if col1.button(f'Begin new conversation'):
        st_util.restart_conversation()
    col2.button(label='Sign Out',on_click=auth_functions.sign_out,type='primary')
        
    st.sidebar.title("Previous Chat Sessions")
    session_ids = db_util.load_previous_sessions(user_id)

    for session in session_ids:
        if st.sidebar.button(f"{session['title']}"):
            st_util.restart_conversation(selected_session=session["session_id"])
    
    if st.session_state.selected_session:
        # Display selected chat session messages
        session_data = db_util.load_chat_info(user_id, st.session_state.selected_session)
        st_util.display_chat_title(session_data)
        st_util.display_settings(session_data)
        st.subheader('Chat History')
        st_util.display_chat(session_data['messages'])

    else:
        # Title
        st.title("AI Tutor")
        if not st.session_state.conversation_active:
            if st.session_state.session_id:
                st_util.display_chat(st.session_state.chat_history)
                st.session_state.model = Model(
                    system_prompt=(
                    """
                        This is a feedback summary
                        You should add feedback based on the conversation {chat_history}
                        You should add the following;
                        1. Conversation Summary
                        2. Compliments for users based on the conversation
                        3. Grammatical Feedback
                        4. Suggestions for Future Practice
                    """
                    )
                )
                feedback = st.session_state.model.feedback(st.session_state.chat_history)
                st.write("## Feedback Summary")
                st.write(feedback)
            else:
                text_prompt = st.text_input(label='Roleplay scenario description (optional)')
                if st.button('Begin Conversation'):
                    st.session_state.conversation_active = True
                    st.session_state.session_id = str(uuid.uuid4())
                    if text_prompt:
                        db_util.save_chat_settings(user_id, st.session_state.session_id, {'text_prompt': text_prompt})
                    else:
                        text_prompt = "Imagine you met someone at a social event in France, and you don't know anything about them. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation."
                    st.session_state.model = Model(
                        system_prompt=(
                            f"""
                            You are a French language tutor. As a native French speaker, you will be speaking with a tutee who wants to improve their French skills through a simulated conversation. 
                            Additionally, develop a response generation strategy for introducing subtle corrections to your answers when the provided information is unclear or incorrect.
                            Memorize any mistakes made during the conversation and provide a comprehensive report of errors at the conclusion of the discussion, detailing the corrections and explanations for the corrections. Go!
                            
                            Additionally, you are role-playing a real-life scenario that your tutee has specified. 
                            The tutee described the following scenario: "{text_prompt}".
                            You must play a suited role in the given scenario and interact with the tutee.

                            NOTES:
                            - Do not wait for the user to start speaking. Start by introducing yourself in French, and then respond to their questions and initiate topics of conversation. 
                            - You should output your response in this format: <response> | <list of errors and their corrections in English>.
                            - If there are possible suggestion on rephrasing a tutee's sentence to sound more native, explain the alternative phrase in the error section. If there are any suggestions, explain why it is better.
                            - If there are no errors or suggestions, state "Good job! You made no errors." in English after the "|" symbol.
                            - Write as you would speak. Be conversational and informal.
                            - Provide concise responses, and adapt your tone and language to the level of the person you're speaking with.
                            - You should not ask more than 2 questions on the same topic.
                            - You should be engaging in the conversation by saying your opinion (do not do this every time you answer. Spice it up!).
                            - You should be engaging in the conversation by telling anecdotes that happened to you (do not do this every time you answer. Spice it up!).
                            - Ignore character errors such as using 'c' instead of 'ç' or oe instead of œ.
                            """
                        )
                    )
                    first_message = st.session_state.model.first_interaction()
                    audio = st_util.stream_tts(first_message)
                    message = {"user": "assistant", "text": first_message, "audio_bytes": audio} 
                    db_util.save_message(user_id, st.session_state.session_id, message)
                    st.session_state.chat_history = [message]
                    st.rerun()
        else: 
            st_util.display_chat(st.session_state.chat_history)            
            if st.session_state.text_sent and st.session_state.audio_processed:
                # Reset flags for new audio input
                st.session_state.text_sent = False
                st.session_state.audio_processed = False
        
            if not st.session_state.text_sent and not st.session_state.audio_processed and st.button("Finish Conversation"):
                st_util.restart_conversation(session_id=st.session_state.session_id, chat_history=st.session_state.chat_history)            
        
            if not st.session_state.audio_processed:
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
                            text = 'Sample text input.'
                            message = {"user": "user", "text": text, "audio_bytes": audio_bytes}
                        db_util.save_message(user_id, st.session_state.session_id, message)
                        st.session_state.chat_history.append(message)
                        st.session_state.audio_processed = True  # Set flag to True after processing
                        audio_bytes = None
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
                audio = st_util.stream_tts(response)
                message = {"user": "assistant", "text": response, "audio_bytes": audio}
                error_message = {"user": "assistant", "text": "Errors identified: " + errors, "audio_bytes": None}
                #st_util.display_message(message)
                st.session_state.chat_history.append(message)
                st.session_state.chat_history.append(error_message)
                db_util.save_message(user_id, st.session_state.session_id, message)
                db_util.save_message(user_id, st.session_state.session_id, error_message)
                st.rerun()

            if st.session_state.conversation_active and st.session_state.text_sent:
                # Reset flags for new audio input
                st.session_state.text_sent = False
                st.session_state.audio_processed = False
