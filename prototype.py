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
if "audio_processing" not in st.session_state:
    st.session_state.audio_processing = False  # Initialize audio_processing
if "response_generated" not in st.session_state:
    st.session_state.response_generated = False  # Initialize response_generated
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None
if "db" not in st.session_state:
    st.session_state.db = firestore.client()
if "model" not in st.session_state:
    st.session_state.model = None

# If logged in
if st.session_state.user is None:
    # Authentication logic
    col1, col2, col3 = st.columns([1, 2, 1])
    auth_form = col2.form(key='Authentication form', clear_on_submit=False)
    email = auth_form.text_input(label='Email')
    password = auth_form.text_input(label='Password', type='password')
    if auth_form.form_submit_button(label='Sign In', type='primary'):
        auth_functions.sign_in(email, password)
else:
    st.title("AI Tutor")
    user_id = st.session_state.user.uid

    st.sidebar.button(label='Sign Out', on_click=auth_functions.sign_out, type='primary')
    if st.sidebar.button('Begin new conversation'):
        st.session_state.chat_history = []
        st.session_state.conversation_active = True
        st.session_state.audio_processed = False
        st.session_state.text_sent = False
        st.session_state.audio_processing = False
        st.session_state.response_generated = False
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
    if st.session_state.conversation_active:
        # Process audio input
        if not st.session_state.audio_processing and not st.session_state.response_generated:
            audio_bytes = audio_recorder(icon_size="4x", pause_threshold=7)
            if audio_bytes:
                st.session_state.audio_processing = True
                text = process_speech_bytes_to_text('wav', audio_bytes, 'audio/wav', lang='fr')
                st.session_state.chat_history.append({"user": "user", "text": text})
                st.session_state.audio_processing = False
                st.session_state.response_generated = True

        # Generate response
        elif st.session_state.response_generated:
            user_text = st.session_state.chat_history[-1]["text"]
            response, errors = st.session_state.model.process(user_text)
            st.session_state.chat_history.append({"user": "assistant", "text": response})
            st.session_state.response_generated = False

        # Display chat history
        st_util.display_chat(st.session_state.chat_history)

        # Finish conversation
        if st.button("Finish Conversation"):
            st.session_state.conversation_active = False
            feedback = generate_feedback(st.session_state.chat_history)
            st.write("## Feedback Summary")
            st.write("### Conversation Summary")
            st.write(feedback["summary"])
            st.write("### Compliments")
            st.write(feedback["compliments"])
            st.write("### Grammatical Feedback")
            st.write(feedback["grammatical_feedback"])
            st.write("### Suggestions for Future Practice")
            st.write(feedback["suggestions"])
