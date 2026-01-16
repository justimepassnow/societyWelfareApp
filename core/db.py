import sqlite3
import hashlib
import pandas as pd
from config import DB_FILE
from datetime import datetime

def get_db_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def setup_database():
    """Set up the database tables if they don't exist."""
    conn = get_db_connection()
    c = conn.cursor()

    # Add columns safely if they don't exist
    try:
        c.execute("ALTER TABLE Users ADD COLUMN PhoneNumber TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute("ALTER TABLE Fund_Lists ADD COLUMN DueDate DATE;")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute("ALTER TABLE Payment_Logs ADD COLUMN Transaction_ID TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists
    try:
        c.execute("ALTER TABLE Users ADD COLUMN Email TEXT;")
    except sqlite3.OperationalError:
        pass # Column already exists

    # User Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            User_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL,
            PasswordHash TEXT NOT NULL,
            Role TEXT NOT NULL CHECK(Role IN ('Admin', 'Member')),
            PhoneNumber TEXT UNIQUE NOT NULL,
            Email TEXT
        )
    ''')

    # Fund Lists Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Fund_Lists (
            List_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            ListName TEXT UNIQUE NOT NULL,
            Amount REAL NOT NULL,
            Interval_Type TEXT NOT NULL CHECK(Interval_Type IN ('Weekly', 'Monthly', 'Quarterly', 'Yearly', 'One-Time')),
            VPA TEXT,
            DueDate DATE
        )
    ''')

    # Memberships Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Memberships (
            Membership_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER NOT NULL,
            List_ID INTEGER NOT NULL,
            FOREIGN KEY (User_ID) REFERENCES Users(User_ID),
            FOREIGN KEY (List_ID) REFERENCES Fund_Lists(List_ID),
            UNIQUE(User_ID, List_ID)
        )
    ''')

    # Payment Logs Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Payment_Logs (
            Log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER NOT NULL,
            List_ID INTEGER NOT NULL,
            Amount REAL NOT NULL,
            DueDate DATE NOT NULL,
            PaymentDate DATE,
            Status TEXT NOT NULL CHECK(Status IN ('Paid', 'Unpaid', 'Pending Verification', 'Rejected')),
            Transaction_ID TEXT,
            FOREIGN KEY (User_ID) REFERENCES Users(User_ID),
            FOREIGN KEY (List_ID) REFERENCES Fund_Lists(List_ID)
        )
    ''')
    
    # Notification Log Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Notification_Log (
            Log_ID INTEGER PRIMARY KEY AUTOINCREMENT,
            User_ID INTEGER NOT NULL,
            List_ID INTEGER NOT NULL,
            SentTimestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (User_ID) REFERENCES Users(User_ID),
            FOREIGN KEY (List_ID) REFERENCES Fund_Lists(List_ID)
        )
    ''')

    # Settings Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # Unverified Transaction IDs Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Unverified_Transaction_IDs (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Log_ID INTEGER,
            Transaction_ID TEXT NOT NULL,
            Submitted_Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (Log_ID) REFERENCES Payment_Logs(Log_ID)
        )
    ''')

    # Verified Transactions Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS Verified_Transactions (
            Transaction_ID TEXT PRIMARY KEY,
            Verified_Timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Add default admin if not exists
    c.execute("SELECT * FROM Users WHERE Username = 'admin'")
    if not c.fetchone():
        hashed_password = hashlib.sha256('admin123'.encode()).hexdigest()
        c.execute("INSERT INTO Users (Username, PasswordHash, Role, PhoneNumber, Email) VALUES (?, ?, ?, ?, ?)",
                  ('admin', hashed_password, 'Admin', '+11234567890', 'admin@example.com')) # Placeholder email




    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM Settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result['value'] if result else None

def set_setting(key, value):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO Settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()



def get_all_payment_logs():
    """Fetches all payment logs with user and fund information."""
    conn = get_db_connection()
    query = """
        SELECT pl.*, u.Username, u.PhoneNumber, fl.ListName 
        FROM Payment_Logs pl
        JOIN Users u ON pl.User_ID = u.User_ID
        JOIN Fund_Lists fl ON pl.List_ID = fl.List_ID
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_fund_options():
    """Fetches all fund lists for display in selectboxes."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT List_ID, ListName FROM Fund_Lists", conn)
    conn.close()
    return df

def create_fund(list_name, amount, interval, due_date, vpa):
    """Creates a new fund list."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO Fund_Lists (ListName, Amount, Interval_Type, VPA, DueDate) VALUES (?, ?, ?, ?, ?)",
                  (list_name, amount, interval, vpa, due_date))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError as e:
        return False, str(e)
    finally:
        conn.close()

def get_all_funds():
    """Fetches all funds for display."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT ListName, Amount, Interval_Type, DueDate, VPA FROM Fund_Lists", conn)
    conn.close()
    return df

def get_member_users():
    """Fetches all users with the 'Member' role."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT User_ID, Username, PhoneNumber, Email FROM Users WHERE Role = 'Member'")
    members = {row['PhoneNumber']: {'User_ID': row['User_ID'], 'Username': row['Username'], 'Email': row['Email']} for row in c.fetchall()}
    conn.close()
    return members
    
def enroll_members(users_to_enroll, payment_logs_to_create):
    """Enrolls members in a fund and creates payment logs."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        if users_to_enroll:
            c.executemany("INSERT OR IGNORE INTO Memberships (User_ID, List_ID) VALUES (?, ?)", users_to_enroll)
        if payment_logs_to_create:
            c.executemany("INSERT INTO Payment_Logs (User_ID, List_ID, Amount, DueDate, Status) VALUES (?, ?, ?, ?, ?)", payment_logs_to_create)
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_members_in_fund(list_id):
    """Fetches all members enrolled in a specific fund."""
    conn = get_db_connection()
    query = "SELECT u.User_ID, u.Username, u.PhoneNumber FROM Users u JOIN Memberships m ON u.User_ID = m.User_ID WHERE m.List_ID = ?"
    df = pd.read_sql_query(query, conn, params=(list_id,))
    conn.close()
    return df

def remove_member_from_fund(user_id, list_id):
    """Removes a member from a fund and deletes their unpaid logs."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM Memberships WHERE User_ID = ? AND List_ID = ?", (user_id, list_id))
        c.execute("DELETE FROM Payment_Logs WHERE User_ID = ? AND List_ID = ? AND Status = 'Unpaid'", (user_id, list_id))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def delete_fund(list_id):
    """Deletes a fund, including all memberships and payment logs."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("BEGIN TRANSACTION;")
        c.execute("DELETE FROM Payment_Logs WHERE List_ID = ?", (list_id,))
        c.execute("DELETE FROM Memberships WHERE List_ID = ?", (list_id,))
        c.execute("DELETE FROM Fund_Lists WHERE List_ID = ?", (list_id,))
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_reminders_preview(list_id=None):
    """Fetches a preview of members with unpaid dues for reminders."""
    conn = get_db_connection()
    base_query = "SELECT u.Username, u.PhoneNumber FROM Payment_Logs pl JOIN Users u ON pl.User_ID = u.User_ID WHERE pl.Status = 'Unpaid'"
    params = []
    if list_id:
        base_query += " AND pl.List_ID = ?"
        params.append(list_id)
    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df

def get_reminders_to_send(list_id=None):
    """Fetches the full details of reminders to be sent."""
    conn = get_db_connection()
    base_query = """
        SELECT pl.User_ID, pl.List_ID, u.Username, u.PhoneNumber, u.Email, fl.ListName, pl.Amount
        FROM Payment_Logs pl
        JOIN Users u ON pl.User_ID = u.User_ID
        JOIN Fund_Lists fl ON pl.List_ID = fl.List_ID
        WHERE pl.Status = 'Unpaid'
    """
    params = []
    if list_id:
        base_query += " AND pl.List_ID = ?"
        params.append(list_id)
    df = pd.read_sql_query(base_query, conn, params=params)
    conn.close()
    return df.to_dict('records')

def log_notification(user_id, list_id):
    """Logs that a notification has been sent to a user for a fund."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO Notification_Log (User_ID, List_ID) VALUES (?, ?)", (user_id, list_id))
        conn.commit()
    except Exception as e:
        print(f"Error logging notification: {e}") # Or use a proper logger
    finally:
        conn.close()

def get_unverified_transactions():
    """Fetches all transaction IDs pending verification."""
    conn = get_db_connection()
    query = """
        SELECT ut.ID, pl.Log_ID, ut.Transaction_ID, u.Username, fl.ListName, pl.Amount
        FROM Unverified_Transaction_IDs ut
        JOIN Payment_Logs pl ON ut.Log_ID = pl.Log_ID
        JOIN Users u ON pl.User_ID = u.User_ID
        JOIN Fund_Lists fl ON pl.List_ID = fl.List_ID
        WHERE pl.Status = 'Pending Verification'
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def verify_transactions(unverified_df, bank_df, txn_id_col, amount_col):
    """Cross-verifies transactions against a bank statement, checking both transaction ID and amount."""
    conn = get_db_connection()
    c = conn.cursor()
    found_txns_details = []
    rejected_txns = [] # This will now be a list of dicts with reasons

    try:
        # --- Data Cleaning ---
        # Handle potential whitespace, quotes, and ensure consistent data types
        bank_df[txn_id_col] = bank_df[txn_id_col].astype(str).str.strip().str.strip("'\"")
        # Additional step to handle potential '.0' suffix for purely numeric IDs
        bank_df[txn_id_col] = bank_df[txn_id_col].apply(lambda x: x.split('.')[0] if isinstance(x, str) and '.' in x and x.replace('.', '').isdigit() else x)

        # Coerce errors will turn non-numeric values into NaN, which are then dropped.
        bank_df[amount_col] = pd.to_numeric(bank_df[amount_col].astype(str).str.strip().str.strip("'\""), errors='coerce')
        bank_df.dropna(subset=[amount_col], inplace=True)
        
        bank_df_indexed = bank_df.set_index(txn_id_col)

        with conn:
            for _, row in unverified_df.iterrows():
                log_id_to_update = row['Log_ID']
                submitted_txn_id = str(row['Transaction_ID']).strip()
                submitted_amount = float(row['Amount'])
                
                rejection_reason = None
                is_approved = False

                if submitted_txn_id in bank_df_indexed.index:
                    # Use .loc and handle potential duplicates by taking the first one
                    bank_record = bank_df_indexed.loc[[submitted_txn_id]].iloc[0]
                    bank_amount = float(bank_record[amount_col])
                    
                    if bank_amount == submitted_amount:
                        is_approved = True
                    else:
                        rejection_reason = f"Amount Mismatch (Bank: {bank_amount}, Submitted: {submitted_amount})"
                else:
                    rejection_reason = "Transaction ID not found in statement"

                if is_approved:
                    # Found and amount matches: Update status to 'Paid'
                    c.execute("UPDATE Payment_Logs SET Status = 'Paid', PaymentDate = ? WHERE Log_ID = ?", 
                              (datetime.now().date(), log_id_to_update))
                    # Add the transaction ID to the permanent verified list
                    c.execute("INSERT OR IGNORE INTO Verified_Transactions (Transaction_ID) VALUES (?)", (submitted_txn_id,))
                    found_txns_details.append({
                        "Transaction ID": submitted_txn_id,
                        "Username": row['Username'],
                        "Fund": row['ListName'],
                        "Amount": submitted_amount
                    })
                else:
                    # ID not found or amount mismatch: Update status to 'Rejected'
                    c.execute("UPDATE Payment_Logs SET Status = 'Rejected' WHERE Log_ID = ?", (log_id_to_update,))
                    rejected_txns.append({
                        "Transaction ID": submitted_txn_id,
                        "Username": row['Username'],
                        "Amount": submitted_amount,
                        "Reason": rejection_reason
                    })
                
                # Remove from unverified table regardless of outcome
                c.execute("DELETE FROM Unverified_Transaction_IDs WHERE ID = ?", (row['ID'],))
                
        return True, found_txns_details, rejected_txns, None
    except Exception as e:
        return False, [], [], str(e)
    finally:
        conn.close()
        
def get_member_dues(user_id):
    """Fetches all outstanding dues for a specific member."""
    conn = get_db_connection()
    query = """
        SELECT pl.Log_ID, fl.ListName, pl.Amount, pl.DueDate, pl.Status 
        FROM Payment_Logs pl 
        JOIN Fund_Lists fl ON pl.List_ID = fl.List_ID 
        WHERE pl.User_ID = ? AND pl.Status IN ('Unpaid', 'Rejected', 'Pending Verification', 'Flagged') 
        ORDER BY pl.DueDate ASC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

def get_fund_vpa(list_name):
    """Fetches the VPA for a specific fund."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT VPA FROM Fund_Lists WHERE ListName = ?", (list_name,))
    result = c.fetchone()
    conn.close()
    return result['VPA'] if result else None

def submit_transaction_for_verification(log_id, transaction_id):
    """Submits a transaction ID for verification by an admin."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        with conn:
            # Update payment log status
            c.execute("UPDATE Payment_Logs SET Status = 'Pending Verification', Transaction_ID = ? WHERE Log_ID = ?", 
                      (transaction_id, log_id))
            # Store transaction ID for admin verification
            c.execute("INSERT INTO Unverified_Transaction_IDs (Log_ID, Transaction_ID) VALUES (?, ?)",
                      (log_id, transaction_id))
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_payment_history(user_id):
    """Fetches the payment history for a specific member."""
    conn = get_db_connection()
    query = """
        SELECT fl.ListName, pl.Amount, pl.DueDate, pl.Status, pl.PaymentDate 
        FROM Payment_Logs pl 
        JOIN Fund_Lists fl ON pl.List_ID = fl.List_ID 
        WHERE pl.User_ID = ? AND pl.Status != 'Unpaid' 
        ORDER BY pl.DueDate DESC
    """
    df = pd.read_sql_query(query, conn, params=(user_id,))
    conn.close()
    return df

def get_fund_details(list_id):
    """Fetches the amount and due date for a specific fund."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT Amount, DueDate FROM Fund_Lists WHERE List_ID = ?", (list_id,))
    result = c.fetchone()
    conn.close()
    return result

def payment_log_exists(user_id, list_id, due_date):
    """Checks if a payment log already exists for a user, fund, and due date."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM Payment_Logs WHERE User_ID = ? AND List_ID = ? AND DueDate = ?", (user_id, list_id, due_date))
    result = c.fetchone()
    conn.close()
    return result is not None

def is_transaction_id_verified(transaction_id):
    """Checks if a transaction ID has already been verified and stored."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT 1 FROM Verified_Transactions WHERE Transaction_ID = ?", (transaction_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def clear_verified_transactions():
    """Clears all records from the Verified_Transactions table."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM Verified_Transactions")
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

def get_verified_transactions():
    """Fetches all stored verified transaction IDs."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT Transaction_ID, Verified_Timestamp FROM Verified_Transactions", conn)
    conn.close()
    return df


def get_recurring_funds():
    """Fetches all funds with a recurring interval type."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM Fund_Lists WHERE Interval_Type != 'One-Time'", conn)
    conn.close()
    return df

def get_memberships():
    """Fetches all membership records."""
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM Memberships", conn)
    conn.close()
    return df

def get_latest_payment_log(user_id, list_id):
    """Fetches the most recent payment log for a specific user and fund."""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "SELECT * FROM Payment_Logs WHERE User_ID = ? AND List_ID = ? ORDER BY DueDate DESC LIMIT 1",
        (user_id, list_id)
    )
    result = c.fetchone()
    conn.close()
    return result

def create_payment_log(user_id, list_id, amount, due_date, status='Unpaid'):
    """Creates a single new payment log entry."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO Payment_Logs (User_ID, List_ID, Amount, DueDate, Status) VALUES (?, ?, ?, ?, ?)",
            (user_id, list_id, amount, due_date, status)
        )
        conn.commit()
        return True, None
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()