from flask import Blueprint, render_template, session, redirect, send_file, url_for
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
