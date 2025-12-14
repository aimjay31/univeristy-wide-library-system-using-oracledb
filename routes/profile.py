from flask import Blueprint, render_template, session, redirect, send_file, url_for, request, flash
from dbconnections.dbconnections import get_connection
import io

bp = Blueprint("profile", __name__)

def _lob_to_bytes(lob):
    if lob is None:
        return None
    if hasattr(lob, "read"):
        return lob.read()
    return lob

@bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    return render_template(
        "profile.html",
        user_id=session["user_id"],
        name=session.get("name"),
        email=session.get("email"),
        role=session.get("role")
    )

@bp.route("/profile_image/<int:user_id>")
def profile_image(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT profile_image FROM users WHERE user_id = :1", (user_id,))
        result = cursor.fetchone()
        if not result or not result[0]:
            # fallback default image
            return send_file("static/default_profile.png", mimetype="image/png")
        data = _lob_to_bytes(result[0])
    finally:
        cursor.close()
        conn.close()

    return send_file(io.BytesIO(data), mimetype="image/png")

@bp.route("/edit_profile", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        role = request.form.get("role")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE users
                SET name = :1, email = :2, role = :3
                WHERE user_id = :4
            """, (name, email, role, user_id))
            conn.commit()
            # Update session
            session["name"] = name
            session["email"] = email
            session["role"] = role
            flash("Profile updated successfully!", "success")
            return redirect(url_for("profile.profile"))
        except Exception as e:
            flash(f"Failed to update profile: {e}", "error")
        finally:
            cursor.close()
            conn.close()

    # GET request
    return render_template(
        "edit_profile.html",
        name=session.get("name"),
        email=session.get("email"),
        role=session.get("role")
    )

@bp.route("/delete_account", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Delete the user
        cursor.execute("DELETE FROM users WHERE user_id = :1", (user_id,))
        conn.commit()

        # Clear session
        session.clear()

        flash("Your account has been deleted.", "success")
        return redirect(url_for("auth.login"))
    except Exception as e:
        flash(f"Failed to delete account: {e}", "error")
        return redirect(url_for("profile.profile"))
    finally:
        cursor.close()
        conn.close()
