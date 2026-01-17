import streamlit as st
import time
from core import auth, db
from core.admin_dashboard import admin_dashboard
from core.member_dashboard import member_dashboard

def login_page():
    st.title("Society Welfare Fund Management System")
    st.header("Login")

    with st.form("login_form"):
        phone_number = st.text_input("Phone Number").lower()
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            user = auth.check_login(phone_number, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user['User_ID']
                st.session_state['username'] = user['Username']
                st.session_state['role'] = user['Role']
                st.session_state['page'] = 'dashboard'
                st.rerun()
            else:
                st.error("Invalid phone number or password.")

    if st.button("Create new account"):
        st.session_state['page'] = 'register'
        st.rerun()

def registration_page():
    st.title("Create Account")

    with st.form("registration_form"):
        new_username = st.text_input("Username (this will be your display name)").lower()
        phone_number = st.text_input("Phone Number (this will be your User ID for login)").lower()
        new_password = st.text_input("Choose a Password", type="password")
        email = st.text_input("Email (Optional)").lower()
        role = st.selectbox("Select Role", ["Member", "Admin"])
        register_button = st.form_submit_button("Register")

        if register_button:
            if new_username and new_password and phone_number:
                success, message = auth.create_user(new_username, new_password, role, phone_number, email)
                if success:
                    st.success("Account created successfully! Please log in.")
                    time.sleep(2)
                    st.session_state['page'] = 'login'
                    st.rerun()
                else:
                    st.error(message)
            else:
                st.warning("Please fill out all fields.")

    if st.button("Back to Login"):
        st.session_state['page'] = 'login'
        st.rerun()

def main():
    """Main function to run the Streamlit app."""
    st.set_page_config(page_title="Welfare Fund Management", layout="wide")
    
    db.setup_database()

    # Initialize session state for page navigation
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['username'] = None
        st.session_state['role'] = None

    # Page routing
    if st.session_state['logged_in']:
        st.sidebar.title(f"Welcome, {st.session_state['username']}")
        if st.sidebar.button("Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state['page'] = 'login'
            st.session_state['logged_in'] = False
            st.rerun()
        
        # Role-based page rendering
        if st.session_state['role'] == 'Admin':
            admin_dashboard()
        elif st.session_state['role'] == 'Member':
            member_dashboard()
        else:
            st.error("Unknown role. Please contact support.")
    
    elif st.session_state['page'] == 'login':
        login_page()
    elif st.session_state['page'] == 'register':
        registration_page()

if __name__ == "__main__":
    main()