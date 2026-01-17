import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import streamlit as st
import pandas as pd
from datetime import datetime
import webbrowser
from urllib.parse import quote
import time
from core import db

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

def admin_dashboard():
    st.header(f"Admin Dashboard | Welcome, {st.session_state['username']}")

    all_logs_df = db.get_all_payment_logs()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "👥 Management", "🔔 Notifications", "🏦 Bulk Verification"])

    # --- FINANCIAL DASHBOARD ---
    with tab1:
        st.subheader("Financial Overview")
        
        if all_logs_df.empty:
            st.info("No financial data available yet.")
        else:
            total_logs = len(all_logs_df)
            paid_logs = all_logs_df[all_logs_df['Status'] == 'Paid']
            total_paid_count = len(paid_logs)
            collection_rate = (total_paid_count / total_logs) * 100 if total_logs > 0 else 0
            total_collected = paid_logs['Amount'].sum()
            total_delinquency = all_logs_df[all_logs_df['Status'].isin(['Unpaid', 'Pending Verification', 'Rejected'])]['Amount'].sum()

            col1, col2, col3 = st.columns(3)
            with col1:
                create_dashboard_card("https://img.icons8.com/plasticine/100/000000/money-bag.png", "Collection Rate", f"{collection_rate:.2f}%", "of total dues collected")
            with col2:
                create_dashboard_card("https://img.icons8.com/plasticine/100/000000/initiate-money-transfer.png", "Total Collected", f"₹{total_collected:,.2f}", "in total revenue")
            with col3:
                create_dashboard_card("https://img.icons8.com/plasticine/100/000000/request-money.png", "Outstanding Dues", f"₹{total_delinquency:,.2f}", "in outstanding payments")

            st.divider()
            st.subheader("Collection Trends")
            if not paid_logs.empty:
                paid_logs['PaymentDate'] = pd.to_datetime(paid_logs['PaymentDate'])
                monthly_collections = paid_logs.set_index('PaymentDate').groupby(pd.Grouper(freq='M'))['Amount'].sum()
                st.bar_chart(monthly_collections)
            else:
                st.info("No paid transactions to display trends.")

            st.divider()
            st.subheader("Outstanding Members per Fund")
            fund_options_financials = db.get_fund_options()
            if not fund_options_financials.empty:
                fund_map_financials = dict(zip(fund_options_financials['ListName'], fund_options_financials['List_ID']))
                selected_fund_name_financials = st.selectbox("Select a fund to view outstanding members", fund_options_financials['ListName'])
                selected_list_id_financials = fund_map_financials[selected_fund_name_financials]
                outstanding_df = all_logs_df[(all_logs_df['List_ID'] == selected_list_id_financials) & (all_logs_df['Status'].isin(['Unpaid', 'Pending Verification', 'Rejected']))]
                st.dataframe(outstanding_df[['Username', 'PhoneNumber', 'Amount', 'DueDate', 'Status']], width='stretch')
            else:
                st.warning("No funds available to filter by.")

    # --- MEMBER & FUND MANAGEMENT ---
    with tab2:
        fund_options = db.get_fund_options()
        fund_map = {row.ListName: row.List_ID for row in fund_options.itertuples(index=False)}

        st.subheader("Fund Configuration")
        with st.expander("Create a New Fund List"):
            with st.form("new_fund_form"):
                list_name = st.text_input("Fund Name (e.g., 'Annual Maintenance')")
                amount = st.number_input("Contribution Amount", min_value=0.01, step=0.50)
                interval = st.selectbox("Recurrence Interval", ['One-Time', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'])
                due_date = st.date_input("Due Date for Payments")
                vpa = st.text_input("UPI ID / VPA (optional)", help="If provided, payments for this fund will go to this specific UPI ID.")

                if st.form_submit_button("Create Fund"):
                    if list_name and amount and due_date:
                        success, error_message = db.create_fund(list_name, amount, interval, due_date.strftime('%Y-%m-%d'), vpa)
                        if success:
                            st.success(f"Fund '{list_name}' created successfully!")
                            st.rerun()
                        else:
                            st.error(f"A fund with this name already exists: {error_message}")

        st.subheader("Existing Funds")
        st.dataframe(db.get_all_funds(), width='stretch')
        st.divider()

        st.subheader("Bulk Member Enrollment")
        if not fund_options.empty:
            selected_fund_name_enroll = st.selectbox("Select Fund to Enroll Members In", fund_options['ListName'], key="enroll_fund_select")
            member_ids_str = st.text_area("Enter Member Phone Numbers (comma-separated)", help="Paste a list of registered member phone numbers, separated by commas. e.g., +11234567890,+12345678901")
            if st.button("Enroll Members"):
                if selected_fund_name_enroll and member_ids_str:
                    member_phone_numbers = [phone.strip() for phone in member_ids_str.split(',') if phone.strip()]
                    selected_list_id = fund_map[selected_fund_name_enroll]
                    
                    fund_info = db.get_fund_details(selected_list_id)
                    due_amount = fund_info['Amount']
                    due_date = fund_info['DueDate']
                    
                    member_users = db.get_member_users()

                    users_to_enroll = []
                    failed_enrollments = []
                    for phone_number in member_phone_numbers:
                        if phone_number in member_users:
                            users_to_enroll.append((member_users[phone_number]['User_ID'], selected_list_id))
                        else:
                            failed_enrollments.append(phone_number)

                    newly_enrolled_user_ids = [u[0] for u in users_to_enroll]
                    payment_logs_to_create = []
                    for user_id in newly_enrolled_user_ids:
                        if not db.payment_log_exists(user_id, selected_list_id, due_date):
                            payment_logs_to_create.append((user_id, selected_list_id, due_amount, due_date, 'Unpaid'))
                    
                    success, error_message = db.enroll_members(users_to_enroll, payment_logs_to_create)

                    if success:
                        successful_enrollments = [f"{member_users[phone]['Username']} ({phone})" for phone in member_phone_numbers if phone not in failed_enrollments]
                        if successful_enrollments:
                            st.success(f"Successfully enrolled {len(successful_enrollments)} members: {', '.join(successful_enrollments)}")
                        if failed_enrollments:
                            st.error(f"Could not find or enroll {len(failed_enrollments)} users: {', '.join(failed_enrollments)}")
                        st.rerun()
                    else:
                        st.error(f"An error occurred: {error_message}")
        else:
            st.warning("Create a fund list first.")
        st.divider()

        st.subheader("Recurring Dues Generation")
        st.info("This will check all recurring funds (Yearly, Monthly, etc.) and generate new payment logs for members if the next billing period has arrived. It will also compound any unpaid dues from the previous period.")
        if st.button("Generate Recurring Dues"):
            with st.spinner("Processing... This may take a moment."):
                try:
                    from core import dues_logic
                    new_logs = dues_logic.update_recurring_dues()
                    if new_logs > 0:
                        st.success(f"Recurring dues updated successfully. {new_logs} new payment log(s) were created.")
                    else:
                        st.info("No new recurring dues to generate at this time.")
                    time.sleep(2) 
                    st.rerun()
                except Exception as e:
                    st.error(f"An error occurred while generating dues: {e}")
        
        st.divider()

        # --- Remove Member from Fund ---
        st.subheader("Remove Member from Fund")
        if not fund_options.empty:
            selected_fund_name_remove = st.selectbox("Select Fund", fund_options['ListName'], key="remove_from_fund")
            selected_list_id_remove = fund_map[selected_fund_name_remove]
            
            members_in_fund_df = db.get_members_in_fund(selected_list_id_remove)

            if not members_in_fund_df.empty:
                members_in_fund_df['display'] = members_in_fund_df.apply(lambda row: f"{row['Username']} ({row['PhoneNumber']})", axis=1)
                member_to_remove_display = st.selectbox("Select Member to Remove", members_in_fund_df['display'])
                
                user_id_to_remove = members_in_fund_df[members_in_fund_df['display'] == member_to_remove_display]['User_ID'].iloc[0]

                if st.button("Remove Member"):
                    if user_id_to_remove:
                        success, error_message = db.remove_member_from_fund(user_id_to_remove, selected_list_id_remove)
                        if success:
                            st.success(f"Removed {member_to_remove_display} from {selected_fund_name_remove} and deleted their unpaid logs.")
                            st.rerun()
                        else:
                            st.error(f"An error occurred: {error_message}")
            else:
                st.info("No members enrolled in this fund.")
        else:
            st.warning("No funds to manage.")
        st.divider()
        
        # --- Delete Fund ---
        st.subheader("Delete a Fund")
        if not fund_options.empty:
            selected_fund_name_delete = st.selectbox("Select Fund to Delete", fund_options['ListName'], key="delete_fund")
            st.warning(f"**DANGER ZONE:** This is permanent and will remove the fund, all memberships, and all payment logs.")
            confirm_delete = st.checkbox(f"I want to permanently delete '{selected_fund_name_delete}'.")
            
            if st.button("Delete Fund Permanently", disabled=not confirm_delete):
                selected_list_id_delete = fund_map[selected_fund_name_delete]
                success, error_message = db.delete_fund(selected_list_id_delete)
                if success:
                    st.success(f"Fund '{selected_fund_name_delete}' was deleted.")
                    st.rerun()
                else:
                    st.error(f"An error occurred: {error_message}")
        else:
            st.warning("No funds to delete.")

    # --- NOTIFICATIONS TAB ---
    with tab3:
        st.subheader("Email Reminder Configuration")
        with st.expander("Configure SMTP Server"):
            with st.form("smtp_config_form"):
                smtp_server = st.text_input("SMTP Server", value=db.get_setting("smtp_server") or "")
                smtp_port = st.number_input("SMTP Port", value=int(db.get_setting("smtp_port") or 587))
                smtp_user = st.text_input("SMTP Username", value=db.get_setting("smtp_user") or "")
                smtp_password = st.text_input("SMTP Password", type="password", value=db.get_setting("smtp_password") or "")
                if st.form_submit_button("Save SMTP Configuration"):
                    db.set_setting("smtp_server", smtp_server)
                    db.set_setting("smtp_port", str(smtp_port))
                    db.set_setting("smtp_user", smtp_user)
                    db.set_setting("smtp_password", smtp_password)
                    st.success("SMTP configuration saved!")
                    
        st.subheader("Send Payment Reminders")
        st.warning("This will attempt to open the WhatsApp desktop app for **each** reminder and send emails if configured. Please ensure you are logged into WhatsApp.")
        
        fund_options_reminders = db.get_fund_options()
        fund_list_reminders = {row.ListName: row.List_ID for row in fund_options_reminders.itertuples(index=False)}
        fund_list_reminders["All Funds"] = 0 
        
        selected_fund_name_reminder = st.selectbox("Select Fund to Send Reminders For", options=list(fund_list_reminders.keys()), index=len(fund_list_reminders)-1)
        
        selected_list_id_reminder = fund_list_reminders[selected_fund_name_reminder]
        
        reminders_preview_df = db.get_reminders_preview(selected_list_id_reminder or None)

        if not reminders_preview_df.empty:
            with st.expander(f"Members to be notified ({len(reminders_preview_df)}):"):
                st.dataframe(reminders_preview_df, width='stretch')
        else:
            st.info("No members with unpaid dues for the selected fund.")

        if st.button("Send Reminders"):
            smtp_server_val = db.get_setting("smtp_server")
            smtp_port_val = db.get_setting("smtp_port")
            smtp_user_val = db.get_setting("smtp_user")
            smtp_password_val = db.get_setting("smtp_password")

            reminders_to_send = db.get_reminders_to_send(selected_list_id_reminder or None)

            if not reminders_to_send:
                st.info("No reminders due to be sent for the selected criteria.")
            else:
                st.info(f"Preparing to send {len(reminders_to_send)} reminders...")

                whatsapp_reminders = 0
                email_reminders = 0

                # Set up SMTP connection if configured
                server = None
                if smtp_server_val and smtp_port_val and smtp_user_val and smtp_password_val:
                    try:
                        server = smtplib.SMTP(smtp_server_val, int(smtp_port_val))
                        server.starttls()
                        server.login(smtp_user_val, smtp_password_val)
                        st.write("✅ SMTP server connected.")
                    except Exception as e:
                        st.error(f"Could not connect to SMTP server: {e}")
                
                for reminder in reminders_to_send:
                    # --- WhatsApp Reminder ---
                    message = f"Hi {reminder['Username']}, this is a friendly reminder that your contribution of ₹{reminder['Amount']} for '{reminder['ListName']}' is due. Please pay via the portal. Thank you!"
                    encoded_message = quote(message)
                    whatsapp_url = f"whatsapp://send?phone={reminder['PhoneNumber']}&text={encoded_message}"
                    
                    try:
                        with st.spinner(f"Opening WhatsApp for {reminder['Username']}..."):
                            webbrowser.open(whatsapp_url)
                            time.sleep(10)
                        
                        db.log_notification(reminder['User_ID'], reminder['List_ID'])
                        st.write(f"✅ WhatsApp reminder for {reminder['Username']} prepared.")
                        whatsapp_reminders += 1

                    except Exception as e:
                        st.error(f"Could not open WhatsApp for {reminder['Username']}: {e}")

                    # --- Email Reminder ---
                    if reminder['Email'] and server:
                        try:
                            msg = MIMEMultipart()
                            msg['From'] = smtp_user_val
                            msg['To'] = reminder['Email']
                            msg['Subject'] = f"Payment Reminder: {reminder['ListName']}"
                            
                            body = f"Dear {reminder['Username']},\n\nThis is a friendly reminder that your contribution of ₹{reminder['Amount']} for '{reminder['ListName']}' is due.\n\nPlease make the payment at your earliest convenience.\n\nThank you,\nSociety Welfare Committee"
                            msg.attach(MIMEText(body, 'plain'))
                            
                            server.send_message(msg)
                            st.write(f"✅ Email reminder sent to {reminder['Username']} at {reminder['Email']}.")
                            email_reminders += 1
                        except Exception as e:
                            st.error(f"Could not send email to {reminder['Username']}: {e}")

                if server:
                    server.quit()

                st.success(f"All reminders processed! Sent {whatsapp_reminders} WhatsApp reminders and {email_reminders} email reminders.")
    # --- BULK VERIFICATION TAB ---
    with tab4:
        st.subheader("Transaction ID Bulk Verification")
        st.info("Here you can verify payments submitted with just a transaction ID by uploading your bank statement.")
        
        unverified_txns_df = db.get_unverified_transactions()
        
        if unverified_txns_df.empty:
            st.info("No transaction IDs are pending verification.")
        else:
            st.write(f"**{len(unverified_txns_df)} transactions pending verification:**")
            st.dataframe(unverified_txns_df[['Transaction_ID', 'Username', 'ListName', 'Amount']], width='stretch')
        
            st.divider()
        
            uploaded_statement = st.file_uploader("Upload Bank Statement (CSV file)", type=['csv'])
            
            if uploaded_statement:
                try:
                    bank_df = pd.read_csv(uploaded_statement)
                    st.write("**Bank Statement Preview:**")
                    st.dataframe(bank_df.head(), width='stretch')

                    txn_id_column = st.selectbox("Which column contains the Transaction IDs?", bank_df.columns)
                    amount_column = st.selectbox("Which column contains the Amount?", bank_df.columns)
                    
                    if st.button("Cross-Verify Transactions"):
                        if txn_id_column and amount_column:
                            success, found_txns_details, rejected_txns, error_message = db.verify_transactions(unverified_txns_df, bank_df, txn_id_column, amount_column)

                            if success:
                                st.success(f"Verification complete! {len(found_txns_details)} transactions were approved and {len(rejected_txns)} were rejected.")
                                
                                if found_txns_details:
                                    st.subheader("Newly Verified Transactions")
                                    st.dataframe(pd.DataFrame(found_txns_details), width='stretch')
                                
                                if rejected_txns:
                                    st.warning("The following transactions were rejected:")
                                    st.dataframe(pd.DataFrame(rejected_txns))
                                
                                if st.button("Acknowledge and Refresh"):
                                    st.rerun()
                            else:
                                st.error(f"An error occurred during verification: {error_message}")
        
                except Exception as e:
                    st.error(f"Failed to process the uploaded file: {e}")

        st.divider()
        
        st.subheader("Previously Verified Transactions")
        verified_txns_df = db.get_verified_transactions()
        if verified_txns_df.empty:
            st.info("No transactions have been verified yet.")
        else:
            st.dataframe(verified_txns_df, width='stretch')

        st.divider()
        st.subheader("Danger Zone")
        st.warning("This will permanently delete the history of all previously verified transaction IDs. This means a member could potentially reuse an old transaction ID. Only do this if you are sure.")
        if st.checkbox("I understand the consequences and want to clear the history."):
            if st.button("Clear All Verified Transaction History"):
                success, error_message = db.clear_verified_transactions()
                if success:
                    st.success("Successfully cleared all verified transaction history!")
                    st.rerun()
                else:
                    st.error(f"An error occurred: {error_message}")