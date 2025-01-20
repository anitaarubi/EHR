from flask import Flask, render_template,request,redirect,flash,session, url_for 
import mysql.connector
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import URLSafeTimedSerializer
import os 

app = Flask(__name__)  #manages the website and keeps track of all pages and decides what page to show.

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Goodlife2021@",
    database = "EHR_System" 
)

mycursor = db.cursor()

# Create tables if they do not already exist
mycursor.execute("CREATE DATABASE IF NOT EXISTS EHR_System")

mycursor.execute("USE EHR_System")

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

for x in tables:
    mycursor.execute(x)
db.commit()

app = Flask(__name__)

# Initialize URLSafeTimedSerializer for generating reset tokens
serializer = URLSafeTimedSerializer(os.urandom(24))  # Secure random key for token generation

def generate_reset_token(email):
    """Generate a reset password token."""
    return serializer.dumps(email, salt="password-reset-salt")

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

            # flash('Registration Successful!')
            return redirect("/login")  # Redirect to login page after success

        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Log the error for debugging
            if err.errno == 1062:  # Duplicate entry error
                flash('Username or email already exists.', 'danger')
            else:
                flash('An error occurred during registration. Please try again.', 'danger')
            return render_template("register.html")  # Show the form again

    # Render registration page on GET request
    return render_template("register.html")

#--------------------------------------------login----------------------------------------------------------------------
@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        email = request.form.get('email')  # Username is entered here
        password = request.form.get('password')  # Password is entered here

        print(f"Received email: {email}")  # Debugging: print email received
        print(f"Received password: {password}")  # Debugging: print password received

        try:
            mycursor = db.cursor(dictionary=True)
            
            # Query for doctor by 'username' field in the database (not 'email')
            mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
            doctor = mycursor.fetchone()
            
            print(f"Doctor found: {doctor}")  # Debugging: print the result of the query

            mycursor.close()

            if doctor:
                # Verify if the password matches the stored hashed password
                if check_password_hash(doctor['password'], password):
                    print(f"Password matched for {doctor['username']}")  # Debugging: successful password match
                    session['doctor_id'] = doctor['id']
                    session['username'] = doctor['username']
                    flash("Login successful!", "success")
                    return redirect("/dashboard")
                else:
                    print("Password does not match")  # Debugging: password mismatch
                    flash("Invalid username or password.", "danger")
            else:
                print("Doctor not found")  # Debugging: doctor not found
            
            return render_template("login.html")  # Re-render the login page with an error message

        except mysql.connector.Error as err:
            print(f"Error: {err}")  # Debugging: print MySQL error
            flash("An error occurred during login.", "danger")
            return render_template("login.html")

    return render_template("login.html")  # For GET request, show the login page

#----------------------------------------forgot password----------------------------------------------------------------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    print("a")
    if request.method == "POST":
        print("ab")
        email = request.form.get('email')
        print(email)
        mycursor = db.cursor()
        mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        doctor = mycursor.fetchone()
        mycursor.close()
        print("B")

        if doctor:
            print("c")
            token = generate_reset_token(email)
            reset_link = url_for("reset_password", token=token, _external=True)
            # Here, you would send the reset email with the token link
            print(reset_link)
            flash("A password reset link has been sent to your email: {reset_link}", "info")
        else:
            print("d")
            flash("Email not found.", "danger")
    
    return render_template("forgot_password.html")
 

@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    email = confirm_reset_token(token)
    if not email:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect("/forgot_password")

    if request.method == "POST":
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template("reset_password.html")

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
            return render_template("reset_password.html")

    return render_template("reset_password.html")


#------------------------------------------dashboard----------------------------------------------------------
#return render_template("login.html")
@app.route("/dashboard")
def dashboard():
    # Check if the doctor is logged in
    if 'doctor_id' not in session:
        # flash("Please log in to access the dashboard.")
        print('doctor id not in session')
        return redirect("/login")    

    doctor_id = session['doctor_id']
    

    try:
        mycursor = db.cursor(dictionary=True)
        mycursor.execute("select * from patients where doctor_id = %s", (doctor_id,))       
        all_patients = mycursor.fetchall()
        print(all_patients)
        mycursor.close()

        # return render_template("dashboard.html", patients=all_patients, recent_ehr=recent_ehr)
        return render_template("dashboard.html", patients=all_patients)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash("An error occurred while loading the dashboard.", "danger")
        print("flash message sent ")
        return redirect("/")

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

        try:
            mycursor = db.cursor()
            mycursor.execute("""
                INSERT INTO patients (doctor_id, first_name, last_name, date_of_birth, gender, contact_info) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (doctor_id, first_name, last_name, date_of_birth, gender, contact_info))
            db.commit()
            mycursor.close()
            flash("Patient added successfully!", "success")
            print("flash message sent ")
            return redirect("/dashboard")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash("Error adding patient.", "danger")

    return render_template("add_patient.html")


#--------------------------------------------------------------------edit patient-----------------------------------------------------------------------------------------------------
@app.route("/edit_patient/<int:patient_id>", methods=["GET", "POST"])
def edit_patient(patient_id):
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        date_of_birth = request.form["date_of_birth"]
        contact_info = request.form["contact_info"]
        gender = request.form["gender"]

        try:
            mycursor = db.cursor()
            mycursor.execute("""
                UPDATE patients 
                SET first_name = %s, last_name = %s, date_of_birth = %s, gender= %s, contact_info = %s 
                WHERE id = %s
            """, (first_name, last_name, date_of_birth, gender, contact_info, patient_id))
            db.commit()
            mycursor.close()
            flash("Patient updated successfully!", "success")
            return redirect("/dashboard")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash("Error updating patient.", "danger")

    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
    patient = mycursor.fetchone()
    mycursor.close()
    return render_template("edit_patient.html", patient=patient)

#-----------------------------------------delete patient----------------------------------------------------------------------

@app.route("/delete_patient/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    try:
        mycursor = db.cursor()
        mycursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
        db.commit()
        mycursor.close()
        flash("Patient deleted successfully!", "success")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash("Error deleting patient.", "danger")
    return redirect("/dashboard")
#----------------------------------------view ehr_data---------------------------------------------------------------
@app.route("/view_ehr/<int:patient_id>")
def view_ehr(patient_id):
    try:
        mycursor = db.cursor(dictionary=True)
        mycursor.execute("""
            SELECT ehr_data.*, patients.first_name, patients.last_name, patients.date_of_birth 
            FROM ehr_data
            JOIN patients ON ehr_data.patient_id = patients.id
            WHERE ehr_data.patient_id = %s
        """, (patient_id,))
        ehr_records = mycursor.fetchall()
        mycursor.close()

        return render_template("view_ehr.html", ehr_records=ehr_records, patient_id=patient_id)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        flash("Error loading EHR data.", "danger")
        return redirect("/dashboard")

#---------------------------------------------add ehr_data-----------------------------------------------------------
@app.route("/add_ehr/<int:patient_id>", methods=["GET", "POST"])
def add_ehr(patient_id):
    print(f"Accessing /add_ehr/{patient_id}")
    if request.method == "POST":
        diagnosis = request.form["diagnosis"]
        medications = request.form["medications"]
        vital_signs = request.form["vital_signs"]
        immunization_status = request.form["immunization_status"]
        medical_history = request.form["medical_history"]
        test_results = request.form["test_results"]
        date = request.form["date"]
        doctor_id = session.get('doctor_id')

        try:
            mycursor = db.cursor()
            mycursor.execute("""
                INSERT INTO ehr_data (patient_id, doctor_id, diagnosis, medications, vital_signs, immunization_status,medical_history, test_results, date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (patient_id, doctor_id, diagnosis, medications, vital_signs, immunization_status, medical_history, test_results, date))
            db.commit()
            mycursor.close()
            flash("EHR added successfully!", "success")
            return redirect(f"/view_ehr/{patient_id}")
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash("Error adding EHR.", "danger")

    return render_template("add_ehr.html", patient_id=patient_id)

#-----------------------------------------------------------------------editing EHR data--------------------------------------------------------------------------------------------
@app.route("/edit_ehr/<int:patient_id>", methods=["GET", "POST"])
def edit_ehr( patient_id):
    if request.method == "POST":
        # Get updated EHR data from the form
        diagnosis = request.form["diagnosis"]
        medications = request.form["medications"]
        vital_signs = request.form["vital_signs"]
        immunization_status = request.form["immunization_status"]
        medical_history = request.form["medical_history"]
        test_results = request.form["test_results"]
        date = request.form["date"]

        try: 

            mycursor = db.cursor()
            # Update the EHR record with the new data
            mycursor.execute("""
                UPDATE ehr_data 
                SET diagnosis = %s, medications = %s, vital_signs = %s, immunization_status = %s, 
                    medical_history = %s, test_results = %s, date = %s 
                WHERE id = %s
            """, (diagnosis, medications, vital_signs, immunization_status, medical_history, test_results, date, patient_id))
            db.commit()
            mycursor.close()
            flash("EHR updated successfully!", "success")
            return redirect("/dashboard")  # Redirect to dashboard after updating
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            flash("Error updating EHR data.", "danger")

    # Fetch the current EHR data for the given `ehr_id`
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM ehr_data WHERE id = %s", ( patient_id,))
    ehr = mycursor.fetchone()
    mycursor.close()

    # Render the EHR edit page with the current data pre-filled
    return render_template("edit_ehr.html",  patient_id=patient_id)


# #----------------------------------------------------------------deleting EHR data-----------------------------------------------------------------------------------------------------
@app.route("/delete_ehr/<int:ehr_id>", methods=["POST"])
def delete_ehr(ehr_id):
    try:
        mycursor = db.cursor()
        # Delete the EHR record based on the provided `ehr_id`
        mycursor.execute("DELETE FROM ehr_data WHERE id = %s", (ehr_id,))
        db.commit()
        mycursor.close()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
    return redirect("/dashboard")  # Redirect to dashboard after deletion#

#---------------------------------------------logout-----------------------------------------------
@app.route("/logout", methods=['POST'])
def logout():
    # Clear session data
    session.clear()
    return redirect(url_for('login'))




if __name__ == "__main__":
    app.secret_key = 'super secret key'
    app.config['SESSION_TYPE'] = 'filesystem'
    app.run(debug=True) #runs the code.
    