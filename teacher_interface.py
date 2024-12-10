import streamlit as st
import firebase_admin
from firebase_admin import firestore, initialize_app, credentials
import pandas as pd

# Initialize Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets['CRED']['firebase_cred']))
    initialize_app(cred)

db = firestore.client()

teacher_id_to_class_id = {
    "mermoud": ["FR1", "FR2", "FR3", "FR4", "FR5", "FR6", "FR7"],
    "aryan": ["DE2", "DE3"],
    "bartholdi": ["DE1"],
    "aitutor": ["0"]
}

def login():
    st.title("Teacher Login")
    teacher_id = st.text_input("Enter your Teacher ID:")
    login_button = st.button("Login")
    
    if login_button:
        if teacher_id in teacher_id_to_class_id:
            st.session_state['class_ids'] = teacher_id_to_class_id[teacher_id]
            st.session_state['logged_in'] = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid Teacher ID. Please try again.")
            return

def load_teacher_interface(class_ids: list[str]=["0"]):
    st.title("AI Tutor - Teacher Dashboard")
    
    # Fetch all students
    students_ref = db.collection('students')
    students = students_ref.stream()

    # Print length of students
    students = list(students_ref.stream())
    # st.write(f"Total number of students: {len(students)}")
    
    student_list = []
    for student in students:
        student_data = student.to_dict()
        print(student_data)
        class_id = student_data.get('class', '0')
        if class_id in class_ids:
            class_name = "None" if class_id == '0' else class_id
            student_list.append({
                'username': student_data.get('username', 'N/A'),
                'class': class_name,
                'last_active': student_data.get('last_active', 'N/A'),
                'id': student_data.get('id', 'N/A'),
            })
    if student_list:
        st.subheader("Student Overview")
        df = pd.DataFrame(student_list)
        df = df[df['id'] != 'N/A']

        # Get number of chats and number of messages for each student
        for index, row in df.iterrows():
            sessions_ref = db.collection('students').document(row['id']).collection('chat_sessions')
            num_chats = len(list(sessions_ref.stream()))
            num_messages = sum(len(session.to_dict().get('messages', [])) for session in sessions_ref.stream())
            df.at[index, 'num_chats'] = num_chats
            df.at[index, 'num_messages'] = num_messages
        st.dataframe(df[['class', 'username', 'last_active', 'num_chats', 'num_messages']], hide_index=True)
        
        selected_student = st.selectbox(
            "Select a student to view chat sessions:",
            options=df['username'].tolist()
        )
        
        if selected_student:
            st.subheader(f"Chat Sessions for {selected_student}")
            selected_student_id = df[df['username'] == selected_student]['id'].values
            if len(selected_student_id) == 0:
                st.error("Student not found")
            else:
                selected_student_id = selected_student_id[0]
                sessions_ref = db.collection('students').document(selected_student_id).collection('chat_sessions')
                sessions = sessions_ref.stream()
                
            for session in sessions:
                session_data = session.to_dict()
                title = session_data.get('title', 'Untitled Session')
                start_time = session_data.get('start_time', 'N/A')
                with st.expander(f"{title} ({start_time})"):
                    if 'settings' in session_data:
                        st.write("Scenario:", session_data['settings'].get('text_prompt', 'N/A'))
                    
                    st.write("Messages:")
                    for msg in session_data.get('messages', []):
                        col1, col2 = st.columns([1, 4])
                        with col1:
                            st.write(f"**{msg.get('user', 'N/A')}:**")
                        with col2:
                            st.write(msg.get('text', 'N/A'))
                            
                    if 'feedback' in session_data:
                        st.write("Feedback:")
                        st.write(session_data['feedback'])

if __name__ == "__main__":
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if not st.session_state['logged_in']:
        login()
    else:
        load_teacher_interface(st.session_state['class_ids'])
