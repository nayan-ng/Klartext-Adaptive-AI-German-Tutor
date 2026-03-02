import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="German Tutor AI", page_icon="🇩🇪")
st.title("🇩🇪 German Tutor AI")

with st.sidebar:
    st.header("⚙️ Settings")
    session_id = st.text_input("Session ID", value="german_session_1")
    
    st.divider()
    st.markdown("*Your FastAPI backend must be running for this to work!*")

if "messages" not in st.session_state:
    st.session_state.messages = []
    
    try:
        response = requests.get(f"{API_URL}/get_history?session_id={session_id}")
        if response.status_code == 200:
            past_chats = response.json()
            for chat in past_chats:
                st.session_state.messages.append({"role": "user", "content": chat["user_input"]})
                st.session_state.messages.append({"role": "assistant", "content": chat["bot_response"]})
    except:
        st.warning("⚠️ Could not connect to the backend. Is FastAPI running?")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Schreib etwas auf Deutsch..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("Denkt nach..."): # Shows a loading spinner
            try:
                # We POST to your /chat endpoint
                res = requests.post(f"{API_URL}/chat?session_id={session_id}&user_message={prompt}")
                if res.status_code == 200:
                    bot_reply = res.json().get("response", "Error getting response")
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    st.error(f"Backend Error: {res.status_code}")
            except Exception as e:
                st.error("Failed to connect to the backend server.")