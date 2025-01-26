from flask import Flask, render_template,request,redirect,flash,session, url_for 
import mysql.connector
from werkzeug.security import generate_password_hash,check_password_hash
from itsdangerous import URLSafeTimedSerializer
import yagmail
import os 

app = Flask(__name__)  #manages the website and keeps track of all pages and decides what page to show.

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Goodlife2021@", #input your own password 
    database = "EHR_System",
    auth_plugin='mysql_native_password'
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

serializer = URLSafeTimedSerializer(os.urandom(24))  # Secure random key for token generation

def generate_reset_token(email):
    """Generate a reset password token."""
    return serializer.dumps(email, salt="password-reset-salt") # these are temporary, one-time-use strings sent to a user's email to allow them to reset their password securely

def confirm_reset_token(token, expiration=3600):
    """ to verify that the token is valid and hasn't expired.."""
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
        email = request.form.get('email') 
        password = request.form.get('password')  
        print(f"Received email: {email}")  # Debugging: print email received
        print(f"Received password: {password}")  # Debugging: print password received


        mycursor = db.cursor(dictionary=True)
            
        # Query for doctor by 'username' field in the database (not 'email')
        mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        doctor = mycursor.fetchone()
            
        print(f"Doctor found: {doctor}")  # Debugging: print the result of the doctor found 

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
            
        return render_template("login.html")  # Re-render the login page with an error message from flash


    return render_template("login.html")

# This function is to send a reset link to user's mail who forgot their password
def send_password_reset_email(to_email, reset_link):
    sender_email = os.getenv("SENDER_EMAIL", "rubimedifo@gmail.com")
    app_password = os.getenv("APP_PASSWORD", "clnnekjbhsxnhsnd")  # Replace with your Gmail app password

    try:
        yag = yagmail.SMTP(sender_email, app_password)
        #This is the email with reset link 
        subject = "Password Reset Request"
        content = f"""
        Hello,
        You have requested to reset your password. Click the link below to reset it:
        {reset_link}
        If you didn't request this, please ignore this email.

        Best regards,
        RubiMed
        """
        # Send the email
        yag.send(to=to_email, subject=subject, contents=content)
        print(f"Password reset email sent to {to_email} successfully!")

    except Exception as e:
        print(f"Failed to send email: {e}")


#----------------------------------------forgot password----------------------------------------------------------------
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email')
        print(email)
        mycursor = db.cursor(buffered=True)
        mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        doctor = mycursor.fetchone()
        print(doctor)
        mycursor.close()

        if doctor:
            token = generate_reset_token(email)
            reset_link = url_for("reset_password", token=token, _external=True)
            send_password_reset_email(email, reset_link)
            # Here, you would send the reset email with the token link
            print(reset_link)
            flash("A password reset link has been sent to your email.", "info")
        else:
            flash("Email not found.", "danger")
    
    return render_template("forgot_password.html")
 
#----------------------------------------reset password----------------------------------------------------------------
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
        print('doctor id not in session')
        return redirect("/login")    

    doctor_id = session['doctor_id']
    
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("select * from patients where doctor_id = %s", (doctor_id,))       
    all_patients = mycursor.fetchall()
    print(all_patients)
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
                WHERE id = %s
            """, (first_name, last_name, date_of_birth, gender, contact_info, patient_id))
        db.commit()
        mycursor.close()
        flash("Patient updated successfully!", "success")
        return redirect("/dashboard")
       
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM patients WHERE id = %s", (patient_id,))
    patient = mycursor.fetchone()
    mycursor.close()
    return render_template("edit_patient.html", patient=patient)

#-----------------------------------------delete patient----------------------------------------------------------------------

@app.route("/delete_patient/<int:patient_id>", methods=["POST"])
def delete_patient(patient_id):
    mycursor = db.cursor()
    mycursor.execute("DELETE FROM patients WHERE id = %s", (patient_id,))
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
            WHERE ehr_data.patient_id = %s
        """, (patient_id,))
    ehr_records = mycursor.fetchall()
    mycursor.close()

    return render_template("view_ehr.html", ehr_records=ehr_records, patient_id=patient_id)

#---------------------------------------------add ehr_data-----------------------------------------------------------
@app.route("/add_ehr/<int:patient_id>", methods=["GET", "POST"])
def add_ehr(patient_id):
    print(f"Accessing /add_ehr/{patient_id}") #debugging errors 
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
        return redirect(f"/view_ehr/{patient_id}")  # Redirect to view ehr page after updating
      
    # Fetch the current EHR data for the given `ehr_id`
    mycursor = db.cursor(dictionary=True)
    mycursor.execute("SELECT * FROM ehr_data WHERE id = %s", ( patient_id,))
    ehr_data = mycursor.fetchone()
    mycursor.close()

    return render_template("edit_ehr.html", patient_id=patient_id, ehr_data=ehr_data)


#----------------------------------------------------------------deleting EHR data-----------------------------------------------------------------------------------------------------
@app.route("/delete_ehr/<int:ehr_id>", methods=["POST"])
def delete_ehr(ehr_id):
    mycursor = db.cursor()
    # Delete the EHR record based on the provided `ehr_id`
    mycursor.execute("DELETE FROM ehr_data WHERE id = %s", (ehr_id,))
    db.commit()
    mycursor.close()
    return redirect("/dashboard")  # Redirect to dashboard after deletion#

#---------------------------------------------logout-----------------------------------------------
@app.route("/logout", methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.secret_key = 'super secret key'
    app.run(debug=True) #runs the code.
    

# I was not able to get the rest password to work as it was very challenging for me ( the chsllenge was more about sending the reset link to the user email) but i just left it there to get feedback to see where i went wrong.