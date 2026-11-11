from flask import Flask, abort, render_template, request, redirect, flash, session, url_for
import mysql.connector
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import URLSafeTimedSerializer
import yagmail
import os

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "local-development-key-change-me")

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "EHR_System"),
}

tables = [
    """
CREATE TABLE IF NOT EXISTS doctors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    email VARCHAR(100)
);
    """,
    """
CREATE TABLE IF NOT EXISTS patients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    doctor_id INT NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender ENUM('Male','Female'),
    contact_info TEXT,
    FOREIGN KEY(doctor_id) REFERENCES doctors(id)
);
    """,
    """
CREATE TABLE IF NOT EXISTS ehr_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    patient_id INT NOT NULL,
    doctor_id INT NOT NULL,
    diagnosis TEXT,
    medications TEXT,
    vital_signs TEXT,
    immunization_status TEXT,
    medical_history TEXT,
    test_results TEXT,
    date DATE,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id) REFERENCES doctors(id)
);
    """
]

def initialize_database():
    """Create the configured database and tables when the app starts."""
    server_config = {key: value for key, value in DB_CONFIG.items() if key != "database"}
    connection = mysql.connector.connect(**server_config)
    cursor = connection.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}`")
    cursor.close()
    connection.close()

    connection = mysql.connector.connect(**DB_CONFIG)
    cursor = connection.cursor()
    for statement in tables:
        cursor.execute(statement)
    connection.commit()
    cursor.close()
    connection.close()


initialize_database()
db = mysql.connector.connect(**DB_CONFIG)

# Initialize URLSafeTimedSerializer for generating reset tokens
serializer = URLSafeTimedSerializer(
    os.getenv("RESET_TOKEN_SECRET", app.config["SECRET_KEY"])
)


@app.before_request
def require_login():
    public_endpoints = {
        "home", "register", "login", "forgot_password", "reset_password", "static"
    }
    if request.endpoint not in public_endpoints and "doctor_id" not in session:
        return redirect(url_for("login"))


def patient_belongs_to_doctor(patient_id, doctor_id):
    cursor = db.cursor()
    cursor.execute(
        "SELECT id FROM patients WHERE id = %s AND doctor_id = %s",
        (patient_id, doctor_id),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None

def generate_reset_token(email):
    """Generate a reset password token."""
    return serializer.dumps(email, salt="password-reset-salt")  # these are temporary, one-time-use strings sent to a user's email to allow them to reset their password securely

def confirm_reset_token(token, expiration=3600):
    """Confirm the reset password token (check validity and expiration)."""
    try:
        email = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
    except Exception as e:
        return None  # Invalid or expired token
    return email

#---------------------------------------------home-----------------------------------------------
@app.route("/")
def home():
    return render_template("home.html")
#---------------------------------------------register----------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Get form inputs
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        # Check for missing fields
        if not username or not password or not email:
            flash("All fields are required", "danger")
            return render_template("register.html")

        # Hash the password
        hashed_password = generate_password_hash(password)

        try:
            # Insert data into the database
            mycursor = db.cursor()
            mycursor.execute(
                "INSERT INTO doctors (username, password, email) VALUES (%s, %s, %s)",
                (username, hashed_password, email)
            )
            db.commit()
            mycursor.close()

            flash('Registration Successful!', 'success')
            return redirect("/login")  # Redirect to login page after successful registration

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template("register.html")  # Shows the form again

    # Render registration page on GET request
    return render_template("register.html")

#--------------------------------------------login----------------------------------------------------------------------
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')  # Username is entered here
        password = request.form.get('password')  # Password is entered here


        try:
            mycursor = db.cursor(dictionary=True)

            # Query for doctor by 'username' field in the database (not 'email')
            mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
            doctor = mycursor.fetchone()


            mycursor.close()

            if doctor:
                # Verify if the password matches the stored hashed password
                if check_password_hash(doctor['password'], password):
                    session['doctor_id'] = doctor['id']
                    session['username'] = doctor['username']
                    flash("Login successful!", "success")
                    return redirect("/dashboard")
                else:
                    flash("Invalid username or password.", "danger")
            else:
                flash("Invalid username or password.", "danger")
            return render_template("login.html")  # Re-render the login page with an error message from flash

        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template("login.html")

    return render_template("login.html")

#---------------------------------define the function to send email to user-------------------------------------------------------------------------
def send_email(email, link):
    username = os.getenv("MAIL_USERNAME")
    password = os.getenv("MAIL_PASSWORD")
    if not username or not password:
        raise RuntimeError("Password reset email is not configured.")
    yag = yagmail.SMTP(username, password)

    message = """Dear User,

    We received a request to reset your password. If you have initiated this request, you can set up a new one by clicking the link below:

    {}

    For your security, this link will expire in 15 minutes.

    If you didn't request this, please ignore this email. Your password will remain unchanged.

    Stay secure,
    Your RubiMed Team""".format(link)

    yag.send(to=email, subject="Reset Password Link", contents=message)

#----------------------------------------forgot password----------------------------------------------------------------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email')

        mycursor = db.cursor(buffered=True)
        mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        doctor = mycursor.fetchone()
        mycursor.close()

        if doctor:
            # Generate a token and a reset link
            token = generate_reset_token(email)
            reset_link = url_for("reset_password", token=token, _external=True)

            # Send the reset email using configured SMTP credentials.
            try:
                send_email(email, reset_link)
            except RuntimeError:
                app.logger.exception("Password reset email is not configured")
                flash("Password reset email is temporarily unavailable.", "danger")
                return render_template("forgot_password.html")

            flash("A password reset link has been sent to your email.", "info")
        else:
            flash("Email not found.", "danger")

    return render_template("forgot_password.html")

#--------------------------------------------------reset password--------------------------------------------------------------------------
@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = confirm_reset_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect("/forgot_password")

    if request.method == "POST":
        password = request.form.get('new-password')
        confirm_password = request.form.get('confirm-password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template("reset_password.html", token=token)

        hashed_password = generate_password_hash(password)

        try:
            mycursor = db.cursor()
            mycursor.execute("UPDATE doctors SET password = %s WHERE email = %s", (hashed_password, email))
            db.commit()
            mycursor.close()
            flash('Your password has been reset successfully.', 'success')
            return redirect("/login")

        except mysql.connector.Error as err:
            flash('An error occurred while resetting your password.', 'danger')
            return render_template("reset_password.html", token=token)

    return render_template("reset_password.html", token=token)


#------------------------------------------------------dashboard-------------------------------------------------------------------------------------------------------
#return render_template("login.html")
@app.route("/dashboard")
def dashboard():
    # Check if the doctor is logged in
    if 'doctor_id' not in session:
        return redirect("/login")

    doctor_id = session['doctor_id']

    mycursor = db.cursor(dictionary=True)
    mycursor.execute("select * from patients where doctor_id = %s", (doctor_id,))
    all_patients = mycursor.fetchall()
    mycursor.close()
    return render_template("dashboard.html", patients=all_patients)

#------------------------------------------------------------------------add patient-------------------------------------------------------------------------------
@app.route("/add_patient", methods=["GET", "POST"])
def add_patient():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        date_of_birth = request.form["date_of_birth"]
        contact_info = request.form["contact"]
        gender = request.form["gender"]
        doctor_id = session.get('doctor_id')

        mycursor = db.cursor()
        mycursor.execute("""
                INSERT INTO patients (doctor_id, first_name, last_name, date_of_birth, gender, contact_info)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (doctor_id, first_name, last_name, date_of_birth, gender, contact_info))
        db.commit()
        mycursor.close()
        flash("Patient added successfully!", "success")
        return redirect("/dashboard")

    return render_template("add_patient.html")


#--------------------------------------------------------------------edit patient-----------------------------------------------------------------------------------------------------
@app.route("/edit_patient/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    if not patient_belongs_to_doctor(patient_id, session['doctor_id']):
        abort(404)
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        date_of_birth = request.form["date_of_birth"]
        contact_info = request.form["contact_info"]
        gender = request.form["gender"]

        mycursor = db.cursor()
        mycursor.execute("""
                UPDATE patients
                SET first_name = %s, last_name = %s, date_of_birth = %s, gender= %s, contact_info = %s
                WHERE id = %s AND doctor_id = %s
            """, (first_name, last_name, date_of_birth, gender, contact_info, patient_id, session['doctor_id']))
        db.commit()
        mycursor.close()
        flash("Patient updated successfully!", "success")
        return redirect("/dashboard")

    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM patients WHERE id = %s AND doctor_id = %s", (patient_id, session['doctor_id']))
    patient = mycursor.fetchone()
    mycursor.close()
    if not patient:
        abort(404)
    return render_template("edit_patient.html", patient=patient)

#-----------------------------------------delete patient----------------------------------------------------------------------

@app.route("/delete_patient/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    mycursor = db.cursor()
    mycursor.execute("DELETE FROM patients WHERE id = %s AND doctor_id = %s", (patient_id, session['doctor_id']))
    db.commit()
    mycursor.close()
    flash("Patient deleted successfully!", "success")
    return redirect("/dashboard")

#----------------------------------------view ehr_data---------------------------------------------------------------
@app.route("/view_ehr/<int:patient_id>")
def view_ehr(patient_id):
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("""
            SELECT ehr_data.*, patients.first_name, patients.last_name, patients.date_of_birth
            FROM ehr_data
            JOIN patients ON ehr_data.patient_id = patients.id
            WHERE ehr_data.patient_id = %s AND patients.doctor_id = %s
        """, (patient_id, session['doctor_id']))
    ehr_records = mycursor.fetchall()
    mycursor.close()

    return render_template("view_ehr.html", ehr_records=ehr_records, patient_id=patient_id)

#---------------------------------------------add ehr_data-----------------------------------------------------------
@app.route("/add_ehr/<int:patient_id>", methods=["GET", "POST"])
def add_ehr(patient_id):
    if not patient_belongs_to_doctor(patient_id, session['doctor_id']):
        abort(404)
    if request.method == "POST":
        diagnosis = request.form["diagnosis"]
        medications = request.form["medications"]
        vital_signs = request.form["vital_signs"]
        immunization_status = request.form["immunization_status"]
        medical_history = request.form["medical_history"]
        test_results = request.form["test_results"]
        date = request.form["date"]
        doctor_id = session.get('doctor_id')

        mycursor = db.cursor()
        mycursor.execute("""
                INSERT INTO ehr_data (patient_id, doctor_id, diagnosis, medications, vital_signs, immunization_status,medical_history, test_results, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, doctor_id, diagnosis, medications, vital_signs, immunization_status, medical_history, test_results, date))
        db.commit()
        mycursor.close()
        flash("EHR added successfully!", "success")
        return redirect(f"/view_ehr/{patient_id}")  # Redirect to view ehr page after adding new record

    return render_template("add_ehr.html", patient_id=patient_id)

#-----------------------------------------------------------------------editing EHR data--------------------------------------------------------------------------------------------
@app.route("/edit_ehr/<int:ehr_id>", methods=["GET", "POST"])
def edit_ehr(ehr_id):
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM ehr_data WHERE id = %s AND doctor_id = %s", (ehr_id, session['doctor_id']))
    ehr_data = mycursor.fetchone()
    mycursor.close()
    if not ehr_data:
        abort(404)

    if request.method == "POST":
        diagnosis = request.form["diagnosis"]
        medications = request.form["medications"]
        vital_signs = request.form["vital_signs"]
        immunization_status = request.form["immunization_status"]
        medical_history = request.form["medical_history"]
        test_results = request.form["test_results"]
        date = request.form["date"]

        mycursor = db.cursor()
        mycursor.execute("""
            UPDATE ehr_data
            SET diagnosis = %s, medications = %s, vital_signs = %s, immunization_status = %s,
                medical_history = %s, test_results = %s, date = %s
            WHERE id = %s AND doctor_id = %s
        """, (diagnosis, medications, vital_signs, immunization_status, medical_history,
              test_results, date, ehr_id, session['doctor_id']))
        db.commit()
        mycursor.close()
        flash("EHR updated successfully!", "success")
        return redirect(url_for("view_ehr", patient_id=ehr_data["patient_id"]))

    return render_template("edit_ehr.html", patient_id=ehr_data["patient_id"], ehr_data=ehr_data)


#----------------------------------------------------------------deleting EHR data-----------------------------------------------------------------------------------------------------
@app.route("/delete_ehr/<int:ehr_id>", methods=["POST"])
def delete_ehr(ehr_id):
    mycursor = db.cursor()
    # Delete the EHR record based on the provided `ehr_id`
    mycursor.execute("DELETE FROM ehr_data WHERE id = %s AND doctor_id = %s", (ehr_id, session['doctor_id']))
    db.commit()
    mycursor.close()
    return redirect("/dashboard")  # Redirect to dashboard after deletion#

#---------------------------------------------logout-----------------------------------------------
@app.route("/logout", methods=['POST'])
def logout():
    # Clear session data
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")

