import streamlit as st
import requests
import os
import time

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Coupon-Ed!", layout="centered")
st.title("Welcome to Coupon-Ed!")

# --- SESSION SETUP ---
if "page" not in st.session_state:
    st.session_state.page = "welcome"

if "user" not in st.session_state:
    st.session_state.user = None

SESSION_TTL = 300  # 5 min


def set_user_session(user_id):
    st.session_state.user = {"userId": user_id, "ts": int(time.time())}
    st.session_state.page = "dashboard"


def get_user_session():
    u = st.session_state.user
    if not u:
        return None
    if int(time.time()) - u["ts"] > SESSION_TTL:
        st.session_state.user = None
        return None
    return u


def logout():
    st.session_state.user = None
    st.session_state.page = "welcome"


# --- DASHBOARD UI ---
def dashboard_ui(sess):
    st.sidebar.success(f"Signed in: {sess['userId']}")
    if st.sidebar.button("Logout"):
        logout()

    st.subheader("Now ACTUALLY... make use of your coupons!")

    tabs = st.tabs(["Upload", "Find", "My Coupons"])

    # --- Upload Tab ---
    with tabs[0]:
        st.subheader("Upload image")
        uploaded_file = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"])

        if st.button("Upload"):
            if not uploaded_file:
                st.error("Choose a file")
            else:
                mime = getattr(uploaded_file, "type", "application/octet-stream")
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), mime)}
                headers = {"X-User-Id": sess["userId"]}
                r = requests.post(f"{API_URL}/upload/", files=files, headers=headers)

                if r.ok:
                    st.success("Coupon Uploaded Successfully!")
                else:
                    st.error(r.text)                    

    # --- Find Tab ---
    with tabs[1]:
        st.subheader("Find coupons")
        user_prompt = st.text_area("Ask something", "I want to buy shoes, do I have any coupons?")

        if st.button("Search"):
            headers = {"X-User-Id": sess["userId"], "Content-Type": "application/json"}
            payload = {
                "user_prompt": user_prompt,
            }
            r = requests.post(f"{API_URL}/find/", json=payload, headers=headers)

            if r.ok:
                st.success("Search completed successfully!")
                st.json(r.json())
            else:
                st.error(r.text)

 # --- My Coupons Tab ---
    with tabs[2]:
        st.subheader("My Coupons")

        headers = {"X-User-Id": sess["userId"]}
        params = {"include_signed_url": True, "include_data": False}
        try:
            r = requests.get(f"{API_URL}/coupons/", headers=headers, params=params, timeout=20)
            if not r.ok:
                st.error(f"Failed to load coupons: {r.text}")
            else:
                data = r.json()
                count = data.get("count", 0)
                st.markdown(f"**Total coupons:** {count}")
                coupons = data.get("coupons", [])
                if not coupons:
                    st.info("No coupons found.")
                else:
                    # Grid display
                    cols_per_row = 3
                    for i in range(0, len(coupons), cols_per_row):
                        row = st.columns(cols_per_row)
                        for col, coupon in zip(row, coupons[i:i+cols_per_row]):
                            with col:
                                url = coupon.get("signed_url")
                                if url:
                                    st.image(url, use_container_width=True)
                                else:
                                    st.warning("No signed URL")
        except Exception as e:
            st.error(f"Exception retrieving coupons: {e}")

# --- LOGIN FORM ---
def login_ui():
    st.subheader("Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        if not username or not password:
            st.error("username and password required")
            return

        r = requests.post(f"{API_URL}/login/", params={"username": username, "password": password})
        if r.ok:
            data = r.json()
            st.success("Login successful")
            set_user_session(data["userId"])
        else:
            st.error(r.text)

    if st.button("Back"):
        st.session_state.page = "welcome"


# --- REGISTER FORM ---
def register_ui():
    st.subheader("Register")

    with st.form("register_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Register")

    if submitted:
        if not username or not password:
            st.error("username and password required")
            return

        r = requests.post(
            f"{API_URL}/users/",
            json={"userName": username, "password": password}
        )

        if r.ok:
            data = r.json()
            st.success("Registered successfully")
            set_user_session(data["userId"])
        else:
            st.error(r.text)

    if st.button("Back"):
        st.session_state.page = "welcome"


# --- WELCOME PAGE ---
def welcome_ui():
    st.subheader("Now ACTUALLY... make use of your coupons!")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            st.session_state.page = "login"
    with col2:
        if st.button("Register"):
            st.session_state.page = "register"


# --- MAIN ROUTER ---
sess = get_user_session()

if sess:
    dashboard_ui(sess)
else:
    if st.session_state.page == "welcome":
        welcome_ui()
    elif st.session_state.page == "login":
        login_ui()
    elif st.session_state.page == "register":
        register_ui()
