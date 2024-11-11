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

def load_previous_sessions(user_id):
    sessions_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions")
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
    session_ref = st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id)
    session_data = session_ref.get().to_dict()
    return session_data['messages']

def delete_chat_history(user_id, session_id):
    st.session_state.selected_session = None
    st.session_state.db.collection("students").document(user_id).collection("chat_sessions").document(session_id).delete()