from flask import Blueprint, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dbconnections.dbconnections import get_connection
from datetime import datetime

bp = Blueprint("auth", __name__, template_folder="templates")

def _lob_to_bytes(lob):
    """Convert Oracle LOB to bytes safely."""
    if lob is None:
        return None
    if hasattr(lob, "read"):
        return lob.read()
    return lob

# ----------------------
# REGISTER
# ----------------------
@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        # Collect and sanitize form data
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        profile_file = request.files.get("profile_image")
        image_bytes = profile_file.read() if profile_file and profile_file.filename else None

        # Basic validation
        if not (name and email and password):
            flash("Please fill in all required fields.", "error")
            return render_template("register.html")

        password_hash = generate_password_hash(password)
        role = "member"  # Force all new users to be 'member'

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Check for duplicate email
            cursor.execute("SELECT COUNT(*) FROM users WHERE email=:1", (email,))
            if cursor.fetchone()[0] > 0:
                flash("Email already exists!", "error")
                return render_template("register.html")

            # Insert new user with optional profile image
            cursor.execute(
                """
                INSERT INTO users
                (name, email, password_hash, role, profile_image, created_at)
                VALUES (:1, :2, :3, :4, :5, :6)
                """,
                (name, email, password_hash, role, image_bytes, datetime.now())
            )
            conn.commit()
            flash("Account created successfully! Please login.", "success")
            return redirect(url_for("auth.login"))

        except Exception as e:
            conn.rollback()
            flash("An error occurred while creating your account.", "error")
            return render_template("register.html")
        finally:
            cursor.close()
            conn.close()

    return render_template("register.html")


# ----------------------
# LOGIN (USER ONLY)
# ----------------------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not (email and password):
            flash("Enter both email and password.", "error")
            return render_template("login.html")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT user_id, name, email, password_hash, role FROM users WHERE email=:1",
                (email,)
            )
            user = cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

        if not user:
            flash("No account found with this email.", "error")
            return render_template("login.html")

        user_id, name, _email, password_hash, role = user

        # ❗ STOP ADMINS HERE
        if role == "admin":
            flash("Administrator accounts must log in through the admin login page.", "error")
            return redirect(url_for("admin.admin_login"))
        
        if role == "librarian":
            # Redirect librarian to their dashboard
            session["user_id"] = int(user_id)
            session["name"] = name
            session["email"] = _email
            session["role"] = role

            flash(f"Welcome, Librarian {name}!", "success")
            return redirect(url_for("librarian.dashboard"))


        # Password validation
        if check_password_hash(password_hash, password):
            session["user_id"] = int(user_id)
            session["name"] = name
            session["email"] = _email
            session["role"] = role

            flash(f"Welcome, {name}!", "success")
            return redirect(url_for("profile.profile"))

        else:
            flash("Incorrect password.", "error")
            return render_template("login.html")

    return render_template("login.html")



# ----------------------
# LOGOUT
# ----------------------
@bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
