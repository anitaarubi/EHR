from itsdangerous import URLSafeTimedSerializer
from datetime import datetime, timedelta
from flask_mail import Mail, Message

# Configure Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@example.com'
app.config['MAIL_PASSWORD'] = 'your_password'
mail = Mail(app)

# Serializer for generating and verifying tokens
s = URLSafeTimedSerializer(app.secret_key)

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form["email"]
        mycursor = db.cursor(dictionary=True)
        mycursor.execute("SELECT * FROM doctors WHERE email = %s", (email,))
        user = mycursor.fetchone()
        mycursor.close()
        
        if user:
            # Generate reset token
            token = s.dumps(email, salt="password-reset-salt")
            expiration_time = datetime.now() + timedelta(hours=1)
            
            # Store token in the database
            mycursor = db.cursor()
            mycursor.execute("""
                UPDATE doctors 
                SET reset_token = %s, token_expiration = %s 
                WHERE email = %s
            """, (token, expiration_time, email))
            db.commit()
            mycursor.close()
            
            # Send email
            reset_link = f"{request.url_root}reset_password/{token}"
            msg = Message("Password Reset Request", sender="your_email@example.com", recipients=[email])
            msg.body = f"Click the link to reset your password: {reset_link}"
            mail.send(msg)
            
            flash("Password reset link has been sent to your email.", "info")
        else:
            flash("Email not found.", "danger")
    
    return render_template("forgot_password.html")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        # Validate the token
        email = s.loads(token, salt="password-reset-salt", max_age=3600)
    except:
        flash("Invalid or expired token.", "danger")
        return redirect("/forgot_password")
    
    if request.method == "POST":
        new_password = request.form["password"]
        hashed_password = generate_password_hash(new_password)
        
        # Update the password in the database
        mycursor = db.cursor()
        mycursor.execute("""
            UPDATE doctors 
            SET password = %s, reset_token = NULL, token_expiration = NULL 
            WHERE email = %s
        """, (hashed_password, email))
        db.commit()
        mycursor.close()
        
        flash("Password has been reset successfully!", "success")
        return redirect("/login")
    
    return render_template("reset_password.html")
