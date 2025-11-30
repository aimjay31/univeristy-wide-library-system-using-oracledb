from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash
from dbconnections.dbconnections import get_connection

bp = Blueprint("admin", __name__, url_prefix="/admin")

# ----------------------
# ADMIN LOGIN
# ----------------------
@bp.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Enter both email and password.", "error")
            return render_template("admin/admin_login.html")

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
            return render_template("admin/admin_login.html")

        user_id, name, _email, password_hash, role = user

        if not check_password_hash(password_hash, password):
            flash("Incorrect password.", "error")
            return render_template("admin/admin_login.html")

        if role != "admin":
            flash("Access denied. Admins only.", "error")
            return render_template("admin/admin_login.html")

        # Valid admin → Log in
        session["user_id"] = int(user_id)
        session["name"] = name
        session["email"] = _email
        session["role"] = role

        flash(f"Welcome, Admin {name}!", "success")
        return redirect(url_for("admin.admin_dashboard"))

    return render_template("admin/admin_login.html")


# -----------------------------------------
# HELPER – CHECK IF USER IS ADMIN
# -----------------------------------------
def require_admin():
    if session.get("role") != "admin":
        flash("Access denied. Admins only.", "error")
        return False
    return True


# -----------------------------
# ADMIN DASHBOARD – VIEW USERS
# -----------------------------
@bp.route("/dashboard")
def admin_dashboard():
    if not require_admin():
        return redirect(url_for("admin.admin_login"))

    search = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        if search:
            # If search is numeric, allow searching by ID as well
            if search.isdigit():
                query = """
                    SELECT user_id, name, email, role
                    FROM users
                    WHERE user_id = :1
                       OR LOWER(name) LIKE :2
                       OR LOWER(email) LIKE :3
                    ORDER BY name
                """
                cursor.execute(query, (int(search), f"%{search.lower()}%", f"%{search.lower()}%"))
            else:
                query = """
                    SELECT user_id, name, email, role
                    FROM users
                    WHERE LOWER(name) LIKE :1
                       OR LOWER(email) LIKE :2
                    ORDER BY name
                """
                cursor.execute(query, (f"%{search.lower()}%", f"%{search.lower()}%"))
        else:
            cursor.execute("SELECT user_id, name, email, role FROM users ORDER BY name")

        users = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("admin/dashboard.html", users=users, search=search)


# -----------------------------
# UPDATE USER ROLE
# -----------------------------
@bp.route("/update_role/<int:user_id>", methods=["POST"])
def update_role(user_id):
    if not require_admin():
        return redirect(url_for("admin.admin_login"))

    new_role = request.form.get("role")

    if new_role not in ["admin", "member", "librarian"]:
        flash("Invalid role.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE users SET role=:1 WHERE user_id=:2", (new_role, user_id))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    flash("Role updated successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@bp.route("/admin_logout")
def admin_logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

# -----------------------------
# DELETE USER
# -----------------------------
@bp.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if not require_admin():
        return redirect(url_for("admin.admin_login"))

    # Prevent admin from deleting themselves
    if session.get("user_id") == user_id:
        flash("You cannot delete your own account.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM users WHERE user_id=:1", (user_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))
