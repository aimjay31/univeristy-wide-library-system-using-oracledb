from flask import Blueprint, render_template, session, redirect

bp = Blueprint("settings", __name__)

@bp.route("/settings")
def settings():
    if "user_id" not in session:
        return redirect("/login")
    return render_template(
        "settings.html",
        name=session.get("name"),
        email=session.get("email"),
        role=session.get("role")
    )
