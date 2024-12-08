import json
import requests
import streamlit as st
from firebase_admin import auth
from datetime import datetime
from firebase_admin import firestore


## -------------------------------------------------------------------------------------------------
## Firebase Auth API -------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in_with_email_and_password(email, password):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def get_account_info(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getAccountInfo?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_email_verification(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "VERIFY_EMAIL", "idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def send_password_reset_email(email):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/getOobConfirmationCode?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"requestType": "PASSWORD_RESET", "email": email})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def create_user_with_email_and_password(email, password):
    # Create new account
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8" }
    data = json.dumps({"email": email, "password": password, "returnSecureToken": True})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def delete_user_account(id_token):
    request_ref = "https://www.googleapis.com/identitytoolkit/v3/relyingparty/deleteAccount?key={0}".format(st.secrets['FIREBASE_WEB_API_KEY'])
    headers = {"content-type": "application/json; charset=UTF-8"}
    data = json.dumps({"idToken": id_token})
    request_object = requests.post(request_ref, headers=headers, data=data)
    raise_detailed_error(request_object)
    return request_object.json()

def raise_detailed_error(request_object):
    try:
        request_object.raise_for_status()
    except requests.exceptions.HTTPError as error:
        raise requests.exceptions.HTTPError(error, request_object.text)

## -------------------------------------------------------------------------------------------------
## Authentication functions ------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------

def sign_in(email:str, password:str) -> None:
    try:
        # Attempt to sign in with email and password
        id_token = sign_in_with_email_and_password(email,password)['idToken']

        # Get account information
        user_info = get_account_info(id_token)["users"][0]

        # If email is not verified, send verification email and do not sign in
        if not user_info["emailVerified"]:
            send_email_verification(id_token)
            st.session_state.auth_warning = 'Check your email to verify your account'

        # Save user info to session state and rerun
        else:
            st.session_state.user_info = user_info
            st.session_state.authorized = True
            st.rerun()

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"INVALID_EMAIL","EMAIL_NOT_FOUND","INVALID_PASSWORD","MISSING_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'

    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def create_account(email:str, password:str, class_id:str='0', username:str=None) -> None:
    try:
        # Create account (and save id_token)
        user_data = create_user_with_email_and_password(email,password)
        id_token = user_data['idToken']
        user_id = user_data['localId']

        if username is None:
            username = email.split('@')[0]

        db = firestore.client()
        db.collection('students').document(user_id).set({
            'id': user_id,
            'email': email,
            'username': username,
            'class': class_id,
            'last_active': datetime.now(),
            'is_guest': False
        })

        # Create account and send email verification
        send_email_verification(id_token)
        st.session_state.auth_success = 'Check your inbox to verify your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message == "EMAIL_EXISTS":
            st.session_state.auth_warning = 'Error: Email belongs to existing account'
        elif error_message in {"INVALID_EMAIL","INVALID_PASSWORD","MISSING_PASSWORD","MISSING_EMAIL","WEAK_PASSWORD"}:
            st.session_state.auth_warning = 'Error: Use a valid email and password'
        else:
            print(error_message)
            st.session_state.auth_warning = 'Error: Please try again later'
    
    except Exception as error:
        print(error)
        st.session_state.auth_warning = 'Error: Please try again later'


def guest_login(username: str, class_id: str) -> dict:
    """
    Create or get guest user in students collection
    Returns user info dictionary if successful
    """
    try:
        db = firestore.client()

        # Check if guest username already exists
        guest_ref = db.collection('students').where('username', '==', username).where('class', '==', class_id).limit(1).stream()
        guest_docs = list(guest_ref)
        
        if not guest_docs:
            # Create new guest user
            new_guest = db.collection('students').document()
            guest_data = {
                'id': new_guest.id,
                'username': username,
                'class': class_id,
                'is_guest': True,
                'last_active': datetime.now()
            }
            new_guest.set(guest_data)
            guest_id = new_guest.id
        else:
            # Use existing guest user
            guest_id = guest_docs[0].id
            db.collection('students').document(guest_id).update({
                'last_active': datetime.now()
            })
        
        return {
            'id': guest_id,
            'username': username,
            'class': class_id,
            'is_guest': True
        }
        
    except Exception as e:
        print(f"Error in guest login: {e}")
        return None


def reset_password(email:str) -> None:
    try:
        send_password_reset_email(email)
        st.session_state.auth_success = 'Password reset link sent to your email'
    
    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        if error_message in {"MISSING_EMAIL","INVALID_EMAIL","EMAIL_NOT_FOUND"}:
            st.session_state.auth_warning = 'Error: Use a valid email'
        else:
            st.session_state.auth_warning = 'Error: Please try again later'    
    
    except Exception:
        st.session_state.auth_warning = 'Error: Please try again later'


def sign_out() -> None:
    #st.session_state.authenticator.logout()
    st.session_state.clear()
    st.session_state.auth_success = 'You have successfully signed out'


def delete_account(password:str) -> None:
    try:
        # Confirm email and password by signing in (and save id_token)
        id_token = sign_in_with_email_and_password(st.session_state.user_info['email'],password)['idToken']
        
        # Attempt to delete account
        delete_user_account(id_token)
        st.session_state.clear()
        st.session_state.auth_success = 'You have successfully deleted your account'

    except requests.exceptions.HTTPError as error:
        error_message = json.loads(error.args[1])['error']['message']
        print(error_message)

    except Exception as error:
        print(error)
        
def google_auth():
    # Catch the login event
    st.session_state.authenticator.check_authentification()
    # Create the login button
    st.session_state.authenticator.login()
    
def login_as_guest(color='white'):
    _,_,col,_,_= st.columns([1,1,1.5,1,1])
    if col.button('Continue as a Guest'):
        st.session_state.user_info = 'guest'
        st.session_state.authorized = True
        st.rerun()
