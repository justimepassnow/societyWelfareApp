import streamlit as st
import pandas as pd
import pyqrcode
from io import BytesIO
import time
from core import db
from config import SOCIETY_VPA, SOCIETY_NAME

def create_dashboard_card(icon, title, value, description):
    st.markdown(
        f"""
        <div class="dashboard-card">
            <img src="{icon}" alt="{title} icon">
            <h3>{title}</h3>
            <p style="font-size: 2rem; font-weight: bold;">{value}</p>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

def member_dashboard():
    st.header(f"Member Dashboard | Welcome, {st.session_state['username']}")
    user_id = st.session_state['user_id']
    
    dues_df = db.get_member_dues(user_id)
    history_df = db.get_payment_history(user_id)

    total_dues = dues_df['Amount'].sum()
    total_paid = history_df[history_df['Status'] == 'Paid']['Amount'].sum()

    col1, col2 = st.columns(2)
    with col1:
        create_dashboard_card("https://img.icons8.com/plasticine/100/000000/request-money.png", "Outstanding Dues", f"₹{total_dues:,.2f}", "Total amount due")
    with col2:
        create_dashboard_card("https://img.icons8.com/plasticine/100/000000/initiate-money-transfer.png", "Total Paid", f"₹{total_paid:,.2f}", "Total amount paid")

    st.divider()

    tab1, tab2 = st.tabs(["💰 My Payments", "📜 Payment History"])

    with tab1:
        st.subheader("Outstanding Dues")
        if dues_df.empty:
            st.success("You have no outstanding dues. Well done! 🎉")
        else:
            def format_due_label(row):
                label = f"{row['ListName']} - ₹{row['Amount']} (Due: {row['DueDate']})"
                if row['Status'] == 'Rejected':
                    label += " - ⚠️ REJECTED"
                elif row['Status'] == 'Pending Verification':
                    label += " - ⏳ PENDING"
                elif row['Status'] == 'Flagged':
                    label += " - 🚩 FLAGGED"
                return label

            due_options = {format_due_label(row): row['Log_ID'] for _, row in dues_df.iterrows()}
            selected_due_str = st.radio("Select a due to pay:", options=due_options.keys())

            if selected_due_str:
                selected_log_id = due_options[selected_due_str]
                details = dues_df[dues_df['Log_ID'] == selected_log_id].iloc[0]
                
                if details['Status'] == 'Pending Verification':
                    st.info("This payment is currently awaiting admin approval. You will be notified once it is processed.")
                else:
                    amount_to_pay, list_name = details['Amount'], details['ListName']
                    
                    target_vpa = db.get_fund_vpa(list_name) or SOCIETY_VPA

                    st.subheader(f"Pay for: {list_name}")
                    if details['Status'] == 'Rejected':
                        st.error("Your previous payment was rejected. Please re-upload a valid transaction ID.")
                    elif details['Status'] == 'Flagged':
                        st.error("Your previous transaction ID could not be found by the admin. Please check the ID and re-submit.")

                    col1, col2 = st.columns([1, 2])

                    with col1:
                        tn = f"M{user_id}L{selected_log_id}"
                        upi_string = f"upi://pay?pa={target_vpa}&pn={SOCIETY_NAME}&am={amount_to_pay}&tn={tn}"
                        qr_code = pyqrcode.create(upi_string)
                        buffer = BytesIO()
                        qr_code.png(buffer, scale=5)
                        st.image(buffer.getvalue(), caption="Scan to Pay", width=200)
                        st.info(f"Amount: ₹{amount_to_pay}")
                        st.caption(f"Paying to: {target_vpa}")
                    
                    with col2:
                        st.write("After paying, enter the 12-digit UPI Transaction ID below.")
                        with st.form("transaction_id_form"):
                            transaction_id = st.text_input("Enter the Transaction ID")
                            submitted = st.form_submit_button("Submit for Verification")
                            
                            if submitted and transaction_id:
                                clean_txn_id = transaction_id.strip()
                                if not (clean_txn_id.isdigit() and len(clean_txn_id) == 12):
                                    st.error("Invalid Transaction ID. Please enter a 12-digit number.")
                                elif db.is_transaction_id_verified(clean_txn_id):
                                    st.error("This transaction ID has already been used and verified. Please use a different one.")
                                else:
                                    success, error_message = db.submit_transaction_for_verification(selected_log_id, clean_txn_id)
                                    if success:
                                        st.success("Transaction ID submitted. An admin will verify it shortly.")
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error(f"An error occurred: {error_message}")
    with tab2:
        st.subheader("Completed and Pending Payments")
        history_df = db.get_payment_history(user_id)
        st.dataframe(history_df, width='stretch')
