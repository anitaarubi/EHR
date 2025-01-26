# Electronic Health Records (EHR) System
## Description
This is a web-based Electronic Health Records (EHR) system built using Flask, MySQL, and Python. The system allows doctors to manage their patients' data, including medical history, diagnoses, medications, and more. It provides functionalities like patient management, password reset, and email notifications.

## Features
**Doctor Registration and Login**: Doctors can register, log in, and manage their account.
**Patient Management:** Doctors can add, edit, and delete patient information.
**EHR Data Management:** Doctors can add and view Electronic Health Records (EHR) data for each patient, such as diagnosis, medications, test results, and medical history.
**Password Reset:** Doctors can reset their password via email using a secure token link.

## Installation
**Clone the repository:**
```
git clone https://github.com/yourusername/EHR-System.git
cd EHR-System
```

**Install dependencies:**
`pip install -r requirements.txt`

**Set up MySQL Database:**
- Create a MySQL database called EHR_System.
- Import the schema for doctors, patients, and EHR data.
Configure environment variables:

## Run the Flask app:
`python app.py`

Access the application by navigating to http://127.0.0.1:5000/ in your web browser.

## Usage
- Register a doctor account and log in.
- Add patients and their respective medical data.
- Reset your password via the "Forgot Password" feature.
- View, edit, or delete patient and medical records.

## Technologies Used
- Flask: Web framework for building the app.
- MySQL: Database for storing patient and doctor data.
- Werkzeug: Password hashing and security.
- Gmail SMTP: For sending password reset emails.
- HTML/CSS/JavaScript: Frontend for the application.
