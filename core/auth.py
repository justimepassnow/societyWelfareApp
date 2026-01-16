import hashlib
import sqlite3
from core.db import get_db_connection

def hash_password(password):
    """Hashes the password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_login(phone_number, password):
    """Checks user credentials against the database."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM Users WHERE PhoneNumber = ?", (phone_number,))
    user = c.fetchone()
    conn.close()
    if user and user['PasswordHash'] == hash_password(password):
        return user
    return None

def create_user(username, password, role, phone_number, email=None):
    """Creates a new user in the database."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO Users (Username, PasswordHash, Role, PhoneNumber, Email) VALUES (?, ?, ?, ?, ?)",
                  (username, hash_password(password), role, phone_number, email))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Username or Phone Number already exists."
    finally:
        conn.close()
