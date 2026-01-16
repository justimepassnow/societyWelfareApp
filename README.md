# Society Welfare Fund Management System

A web-based application built with Streamlit to manage welfare fund contributions for a society or community. This application provides separate dashboards for administrators and members to streamline the process of fund management, payment tracking, and communication.

## Features

### Admin Dashboard
- **Financial Overview:**
    - Track key metrics like collection rate, total amount collected, and outstanding dues.
    - Visualize collection trends over time.
- **Fund Management:**
    - Create and manage different types of funds (e.g., annual maintenance, special events).
    - Configure fund details such as contribution amount, recurrence interval (one-time, monthly, yearly), and due dates.
- **Member Management:**
    - Enroll members into various funds.
    - Remove members from funds.
    - View members with outstanding payments for specific funds.
- **Automated Dues Generation:**
    - Automatically generate recurring dues for members based on the fund's interval.
    - Compound unpaid dues from previous periods.
- **Notifications:**
    - Send payment reminders to members with outstanding dues via WhatsApp and email.
    - SMTP server configuration for sending email reminders.
- **Bulk Payment Verification:**
    - Verify payments in bulk by uploading a bank statement (CSV).
    - Cross-verify transaction IDs and amounts to approve or reject payments.

### Member Dashboard
- **View and Pay Dues:**
    - View a list of all outstanding dues.
    - Generate a UPI QR code for easy payment.
    - Submit the UPI transaction ID for verification after payment.
- **Payment History:**
    - View a history of all completed, pending, and rejected payments.

## Technologies Used

- **Frontend:** Streamlit
- **Backend:** Python
- **Database:** SQLite
- **Libraries:**
    - pandas
    - pyqrcode
    - watchdog

## Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd society-welfare-app
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**
    -   **Windows:**
        ```bash
        .\venv\Scripts\activate
        ```
    -   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## How to Run

To run the application, navigate to the project directory in your terminal and execute the following command:

```bash
streamlit run app.py
```

The application will open in your web browser. You can log in with the default admin credentials:
- **Phone Number:** `+11234567890`
- **Password:** `admin123`
