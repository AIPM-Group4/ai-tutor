import streamlit as st
import utils.auth_functions as auth_functions
import utils.db_util as db_util
import utils.streamlit_utils as st_util
from firebase_admin import auth

from transcribe import process_speech_bytes_to_text
from dialogue import Model
import firebase_admin
from firebase_admin import firestore, initialize_app, credentials
from utils.streamlit_google_auth import Authenticate
from audio_recorder_streamlit import audio_recorder
import uuid
from streamlit_javascript import st_javascript
from user_agents import parse

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

ua_string = str(st_javascript("""window.navigator.userAgent;"""))
user_agent = parse(ua_string)

if "is_mobile" not in st.session_state:
    st.session_state.is_mobile = not user_agent.is_pc

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

if "show_transcription" not in st.session_state:
    st.session_state.show_transcription = True  # Default to showing transcriptions

#Google Auth Currently turned off.
#if "authenticator" not in st.session_state:
#    st.session_state.authenticator = Authenticate(
#        secret_credentials_config = dict(st.secrets['CRED']['oauth_cred']),
#        cookie_name='my_cookie_name',
#        cookie_key='this_is_secret',
#        redirect_uri = 'https://aitutor-epfl.streamlit.app',
#    ) 
if "authorized" not in st.session_state:
    st.session_state.authorized = None
if "language" not in st.session_state:
    st.session_state.language = None

# Add this right after your imports and before any other code
st.markdown("""
    <style>
        #feedback-button {
            position: fixed;
            bottom: 20px;
            right: 20px;
            background-color: #FF4B4B;
            color: white;
            padding: 15px 32px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 4px;
            border: none;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            z-index: 999;
        }
        #feedback-button:hover {
            background-color: #FF2E2E;
        }
        /* Adjust main content to not be hidden by the feedback button */
        .main .block-container {
            padding-bottom: 80px;
        }
    </style>
    <a href="https://docs.google.com/forms/d/e/1FAIpQLSfzXOawMjCUzO2wnwpf5feI1aDlHaCe6IClZEiU2dPqoU8VdQ/viewform?usp=sf_link" target="_blank" id="feedback-button">
        Please give feedback once you are done with the app! (Even if you had issues with it.)
    </a>
""", unsafe_allow_html=True)

# If not logged in.
if not st.session_state.user_info or not st.session_state.authorized:
    # Markdown with HTML title
    st.markdown("<h1 style='text-align: center;'>AI Tutor</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    
    # Add login type selection
    login_type = col2.radio("Choose how to enter:", ["I have a class ID", "I do not have a class ID"])
    auth_form = col2.form(key='Authentication form', clear_on_submit=False)
    auth_notification = col2.empty()

    if login_type == "I have a class ID":
         # Guest access form
        username = auth_form.text_input(label='Username')
        class_id = auth_form.text_input(label='Class ID')
        if "DE" in class_id:
            language = "Deutsch"
        else:
            language = "Français"
        
        if auth_form.form_submit_button(label='Enter as Guest', use_container_width=True, type='primary'):
            if username and class_id:
                guest_info = auth_functions.guest_login(username, class_id)
                if guest_info:
                    st.session_state.user_info = guest_info
                    st.session_state.authorized = True
                    st.session_state.language = language
                    st.rerun()
                else:
                    auth_notification.error('Error logging in as guest. Please try again.')
            else:
                auth_notification.error('Please enter both username and class ID')

    elif login_type == "I do not have a class ID":
        # Guest access form
        username = auth_form.text_input(label='Username')
        language = auth_form.selectbox(label='Language', options=['Français', 'Deutsch'])
        # class_id = auth_form.text_input(label='Class ID')
        
        if auth_form.form_submit_button(label='Enter as Guest', use_container_width=True, type='primary'):
            if username:
                guest_info = auth_functions.guest_login(username, '0')
                if guest_info:
                    st.session_state.user_info = guest_info
                    st.session_state.authorized = True
                    st.session_state.language = language
                    print(st.session_state.language)
                    st.rerun()
                else:
                    auth_notification.error('Error logging in as guest. Please try again.')
            else:
                auth_notification.error('Please enter both username and class ID')
    
    # elif login_type == "Sign In":
    #     # Regular sign in form
    #     email = auth_form.text_input(label='Email')
    #     password = auth_form.text_input(label='Password', type='password')
        
    #     if auth_form.form_submit_button(label='Sign In', use_container_width=True, type='primary'):
    #         with auth_notification, st.spinner('Signing in'):
    #             auth_functions.sign_in(email, password)
    
    # elif login_type == "Create Account":
    #     # Account creation form
    #     email = auth_form.text_input(label='Email')
    #     password = auth_form.text_input(label='Password', type='password')
    #     available_classes = ['Class A', 'Class B', 'Class C', 'Unassigned']
    #     class_id = auth_form.selectbox('Select Class', options=available_classes)
        
    #     if auth_form.form_submit_button(label='Create Account', use_container_width=True, type='primary'):
    #         with auth_notification, st.spinner('Creating account'):
    #             auth_functions.create_account(email, password, class_id)
    
    # elif login_type == "Forgot Password":
    #     # Password reset form
    #     email = auth_form.text_input(label='Email')
        
    #     if auth_form.form_submit_button(label='Send Password Reset Email', use_container_width=True, type='primary'):
    #         with auth_notification, st.spinner('Sending password reset link'):
    #             auth_functions.reset_password(email)

# # If not logged in.
# if not st.session_state.user_info or not st.session_state.authorized:
#     # Markdown with HTML title because st functions weren't working so great
#     st.markdown("<h1 style='text-align: center; color: black;'>AI Tutor</h1>", unsafe_allow_html=True)
#     col1,col2,col3 = st.columns([1,2,1])
#     auth_functions.login_as_guest()

#     # Authentication form layout
#     do_you_have_an_account = col2.selectbox(label='Do you have an account?',options=('Yes','No','I forgot my password'))
#     auth_form = col2.form(key='Authentication form',clear_on_submit=False)
#     email = auth_form.text_input(label='Email')
#     password = auth_form.text_input(label='Password',type='password') if do_you_have_an_account in {'Yes','No'} else auth_form.empty()
#     auth_notification = col2.empty()

#     # Sign In
#     if do_you_have_an_account == 'Yes' and auth_form.form_submit_button(label='Sign In',use_container_width=True,type='primary'):
#         with auth_notification, st.spinner('Signing in'):
#             auth_functions.sign_in(email,password)

#     # Create Account
#     elif do_you_have_an_account == 'No' and auth_form.form_submit_button(label='Create Account',use_container_width=True,type='primary'):
#         with auth_notification, st.spinner('Creating account'):
#             auth_functions.create_account(email,password,"0")

#     # Password Reset
#     elif do_you_have_an_account == 'I forgot my password' and auth_form.form_submit_button(label='Send Password Reset Email',use_container_width=True,type='primary'):
#         with auth_notification, st.spinner('Sending password reset link'):
#             auth_functions.reset_password(email)

    # Authentication success and warning messages
    if 'auth_success' in st.session_state:
        auth_notification.success(st.session_state.auth_success)
        del st.session_state.auth_success
    elif 'auth_warning' in st.session_state:
        auth_notification.warning(st.session_state.auth_warning)
        del st.session_state.auth_warning

# If logged in
else:
    try:
        user_id = st.session_state.user_info['id']
        # # If account created by email
        # email = st.session_state.user_info["email"]
        # user = auth.get_user_by_email(email)
        # user_id = user.uid
    except:
        if 'oauth_id' in st.session_state:
            user_id = st.session_state.oauth_id
        else:
            user_id = None
        
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
    
    if user_id: # If not Guest Login
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
            st_util.display_feedback(session_data)
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
            db_util.save_feedback(user_id, st.session_state.session_id, feedback)
        else:
            text_prompt = st.text_input(label='Roleplay scenario description (optional)')
            if st.button('Begin Conversation'):
                st.session_state.conversation_active = True
                st.session_state.session_id = str(uuid.uuid4())
                if text_prompt:
                    db_util.save_chat_settings(user_id, st.session_state.session_id, {'text_prompt': text_prompt})
                else:
                    text_prompt = f"Hello, I would like to practice my {"German" if st.session_state.language == "Deutsch" else "French"}. Can you please start an engaging conversation in this language with me. Introduce yourself and then suggest three topics of conversation and let me choose one. The topics should be role-play scenarios of everyday life."
                
                st.session_state.model = Model(
                    system_prompt=(
                        f"""
                        You are a language tutor. As a native {st.session_state.language} speaker, you will be speaking with a tutee who wants to improve their {st.session_state.language} skills through a simulated conversation. 
                        Additionally, develop a response generation strategy for introducing subtle corrections to your answers when the provided information is unclear or incorrect.
                        Memorize any mistakes made during the conversation and provide a comprehensive report of errors at the conclusion of the discussion, detailing the corrections and explanations for the corrections. Go!
                        
                        Additionally, you are role-playing a real-life scenario that your tutee has specified. 
                        The tutee described the following scenario: "{text_prompt}".
                        You must play a suited role in the given scenario and interact with the tutee.

                        NOTES:
                        - Your voice is female, so choose a female name.
                        - Do not wait for the user to start speaking. Start by introducing yourself in the target language, and then respond to their questions and initiate topics of conversation. 
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
                    ),
                    language=st.session_state.language
                )
                first_message = st.session_state.model.first_interaction()
                audio, translated_text = st_util.stream_tts(first_message, translation=True, lang=st.session_state.language)
                message = {"user": "assistant", "text": first_message, "audio_bytes": audio, "translated_text": translated_text} 
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
                        lang = 'fr' if st.session_state.language == "Français" else 'de' if st.session_state.language == "Deutsch" else 'en'
                        try:
                            text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav', lang=lang)
                        except Exception as e:
                            pass
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
            audio, translated_text = st_util.stream_tts(response, translation=True, lang=st.session_state.language)
            message = {"user": "assistant", "text": response, "audio_bytes": audio, "translated_text": translated_text}
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
