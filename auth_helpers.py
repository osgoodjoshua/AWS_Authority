import streamlit as st
import requests
import os
from urllib.parse import urlencode
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL")
AUTH0_LOGOUT_URL = os.getenv("AUTH0_LOGOUT_URL")

def login():
    # Generate Auth0 login URL
    query_params = {
        "client_id": AUTH0_CLIENT_ID,
        "redirect_uri": AUTH0_CALLBACK_URL,
        "response_type": "code",
        "scope": "openid profile email",
    }
    auth_url = f"https://{AUTH0_DOMAIN}/authorize?" + urlencode(query_params)
    st.markdown(f"[Login]({auth_url})", unsafe_allow_html=True)

def handle_callback():
    # Check for the "code" parameter in query_params
    query_params = st.query_params
    if "code" not in query_params:
        # st.error("Authorization code not found in callback URL.")
        return None

    code = query_params["code"]

    # Exchange the code for tokens
    token_url = f"https://{AUTH0_DOMAIN}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": AUTH0_CLIENT_ID,
        "client_secret": AUTH0_CLIENT_SECRET,
        "code": code,
        "redirect_uri": AUTH0_CALLBACK_URL,
    }

    response = requests.post(token_url, json=payload)

    if response.status_code != 200:
        st.error(f"Failed to fetch access token: {response.json()}")
        return None

    tokens = response.json()

    # Ensure 'access_token' exists
    if "access_token" not in tokens:
        st.error("Access token not found in response.")
        st.write(tokens)  # Debugging output
        return None

    # Fetch user information using access token
    user_info_url = f"https://{AUTH0_DOMAIN}/userinfo"
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    user_info_response = requests.get(user_info_url, headers=headers)

    if user_info_response.status_code != 200:
        st.error("Failed to fetch user information.")
        st.write(user_info_response.json())  # Debugging output
        return None

    # Store user info in session state
    user_info = user_info_response.json()
    st.session_state["user"] = user_info
    return user_info

def logout():
    if "user" in st.session_state:
        del st.session_state["user"]

    logout_url = (
        f"https://{AUTH0_DOMAIN}/v2/logout?"
        f"client_id={AUTH0_CLIENT_ID}&"
        f"returnTo={AUTH0_LOGOUT_URL}"
    )
    st.markdown(
        f'<meta http-equiv="refresh" content="0; URL={logout_url}">',
        unsafe_allow_html=True,
    )

def get_user():
    return st.session_state.get("user", None)
