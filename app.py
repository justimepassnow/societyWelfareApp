import streamlit as st
import time
from core import auth, db
from core.admin_dashboard import admin_dashboard
from core.member_dashboard import member_dashboard

def apply_global_style():
    st.markdown(
        """
        <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1e3a8a;
            --accent: #22c55e;
            --text: #0f172a;
            --muted: #64748b;
            --card: #ffffff;
            --border: #e2e8f0;
        }

        .stApp {
            background: radial-gradient(circle at top, #eef2ff 0%, #f8fafc 55%, #ffffff 100%);
            color: var(--text);
        }

        .stApp header, .stApp footer {
            background: transparent;
        }

        [data-testid="stSidebar"] {
            background: #0f172a;
            color: #f8fafc;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] p,
        [data-testid="stSidebar"] span {
            color: #f8fafc;
        }

        div[data-testid="stForm"] {
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 1.75rem 2rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.08);
        }

        .hero-card {
            background: linear-gradient(120deg, rgba(37, 99, 235, 0.1), rgba(34, 197, 94, 0.1));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 2rem;
            margin-bottom: 1.5rem;
        }

        .hero-card h1 {
            margin-bottom: 0.25rem;
        }

        .hero-card p {
            color: var(--muted);
        }

        .info-pill {
            display: inline-block;
            padding: 0.4rem 0.75rem;
            border-radius: 999px;
            background: #eff6ff;
            color: #1d4ed8;
            font-weight: 600;
            font-size: 0.85rem;
            margin-right: 0.5rem;
        }

        .stButton > button {
            background: linear-gradient(90deg, #2563eb, #1d4ed8);
            color: #ffffff;
            border-radius: 10px;
            border: none;
            padding: 0.6rem 1.25rem;
            font-weight: 600;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            box-shadow: 0 10px 20px rgba(37, 99, 235, 0.2);
        }

        .stButton > button:hover {
            transform: translateY(-1px);
            box-shadow: 0 14px 26px rgba(37, 99, 235, 0.25);
        }

        .stButton > button:focus {
            outline: 2px solid #93c5fd;
            outline-offset: 2px;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 0.5rem;
        }

        .stTabs [data-baseweb="tab"] {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 0.4rem 1rem;
        }

        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: #1d4ed8;
            color: #ffffff;
            border-color: #1d4ed8;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border-radius: 16px;
            padding: 1rem;
            border: 1px solid var(--border);
            box-shadow: 0 12px 25px rgba(15, 23, 42, 0.06);
        }

        div[data-testid="stMetric"] label {
            color: var(--muted);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def login_page():
    st.markdown(
        """
        <div class="hero-card">
            <span class="info-pill">Secure Access</span>
            <span class="info-pill">Member & Admin</span>
            <h1>Society Welfare Fund Management System</h1>
            <p>Track contributions, manage funds, and keep your community finances organized.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
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
    st.markdown(
        """
        <div class="hero-card">
            <span class="info-pill">Quick Setup</span>
            <span class="info-pill">Secure Profiles</span>
            <h1>Create your account</h1>
            <p>Join the society portal in minutes to manage your dues and stay updated.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
    apply_global_style()
    
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
