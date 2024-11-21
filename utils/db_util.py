from firebase_admin import firestore
import datetime
import streamlit as st

def save_message(user_id, session_id, message):
        session_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
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

def save_chat_settings(user_id, session_id, settings):
    session_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
    if not session_ref.get().exists:
        session_ref.set({
            "start_time": datetime.datetime.now(),
            "messages": []
        })
    
    session_ref.update({
        "settings": settings
    })

def save_new_title(user_id, session_id, new_title):
    session_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
    session_ref.update({
        "title": new_title
    })

def load_previous_sessions(user_id):
    sessions_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions")
    sessions = sessions_ref.order_by("start_time", direction=firestore.Query.DESCENDING).stream()
    
    session_ids = []
    for session in sessions:
        session_data = session.to_dict()
        start_time = f'{session_data.get("start_time"):%Y-%m-%d %H:%M:%S}'
        if 'title' not in session_data:
            session_data['title'] = f'Session {start_time}'
            sessions_ref.document(session.id).update({
                "title": session_data['title']
            })
        session_ids.append({
            "session_id": session.id,
            "start_time": start_time,
            "title": session_data['title']
        })
    return session_ids

def load_chat_info(user_id, session_id):
    session_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
    session_data = session_ref.get().to_dict()
    return session_data

def delete_chat_history(user_id, session_id):
    st.session_state.selected_session = None
    st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id).delete()