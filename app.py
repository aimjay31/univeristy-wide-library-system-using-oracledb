from flask import Flask, session, redirect, url_for, request
from routes import auth, profile, books, settings, admin, librarian, user_library


app = Flask(__name__)
app.secret_key = "supersecretkey"  # change to env var in production

# Register Blueprints
app.register_blueprint(auth.bp)
app.register_blueprint(profile.bp)
app.register_blueprint(books.bp)
app.register_blueprint(settings.bp)
app.register_blueprint(admin.bp)
app.register_blueprint(librarian.bp)
app.register_blueprint(user_library.bp)

# ----------------------
# PROTECT ROUTES
# ----------------------
@app.before_request
def require_login():
    # Use Blueprint-qualified endpoints
    allowed = {
        "auth.login",
        "auth.register",
        "profile.profile_image",
        "admin.admin_login",
        "static",
        None
    }

    # Redirect unauthenticated users
    if "user_id" not in session and request.endpoint not in allowed:
        return redirect(url_for("auth.login"))

if __name__ == "__main__":
    app.run(debug=True)
