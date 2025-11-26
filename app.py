from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dbconnections.dbconnections import get_connection
from datetime import datetime
import base64

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ----------------------
# REGISTER
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        password_hash = generate_password_hash(password)

        conn = get_connection()
        cursor = conn.cursor()

        # Check for duplicate email
        cursor.execute("SELECT COUNT(*) FROM users WHERE email=:1", (email,))
        exists = cursor.fetchone()[0]

        if exists > 0:
            flash("Email already exists!", "error")
            cursor.close()
            conn.close()
            return render_template("register.html")

        # Insert new user
        cursor.execute(
            "INSERT INTO users (name, email, password_hash, role, created_at) VALUES (:1, :2, :3, :4, :5)",
            (name, email, password_hash, role, datetime.now())
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("Account created successfully! Please login.", "success")
        return redirect("/login")

    return render_template("register.html")


# ----------------------
# LOGIN
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, name, email, password_hash, role, profile_image FROM users WHERE email=:1",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user is None:
            flash("Account does not exist. Please register.", "error")
            return render_template("login.html")

        if check_password_hash(user[3], password):
            session["user_id"] = user[0]
            session["name"] = user[1]
            session["email"] = user[2]
            session["role"] = user[4]

            # Store profile image as base64 if exists
            if user[5]:
                session["profile_image"] = base64.b64encode(user[5].read()).decode("utf-8")
            else:
                session["profile_image"] = None

            flash(f"Welcome, {user[1]}!", "success")
            return redirect("/profile")
        else:
            flash("Incorrect password. Try again.", "error")
            return render_template("login.html")

    return render_template("login.html")


# ----------------------
# LOGOUT
# ----------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "info")
    return redirect("/login")


# ----------------------
# PROFILE
# ----------------------
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "profile.html",
        name=session["name"],
        email=session["email"],
        role=session["role"],
        profile_image=session.get("profile_image")
    )


# ----------------------
# PROTECT ROUTES
# ----------------------
@app.before_request
def require_login():
    allowed_routes = ["login", "register", "static"]
    if request.endpoint not in allowed_routes and "user_id" not in session:
        return redirect("/login")


# ----------------------
# HOME / SEARCH BOOKS
# ----------------------
@app.route('/')
def index():
    search_type = request.args.get("filter")
    keyword = request.args.get("keyword")
    sort = request.args.get("sort")

    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT book_id, title, author, year_published, university FROM university_books"
    params = []

    if keyword:
        keyword_param = f"%{keyword.lower()}%"
        if search_type == "university":
            query += " WHERE LOWER(university) LIKE :keyword"
        elif search_type == "author":
            query += " WHERE LOWER(author) LIKE :keyword"
        elif search_type == "title":
            query += " WHERE LOWER(title) LIKE :keyword"
        params = [keyword_param]

    if sort:
        query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    books = [
        {"id": r[0], "title": r[1], "author": r[2], "year": r[3], "university": r[4]}
        for r in cursor
    ]

    cursor.close()
    conn.close()

    return render_template('index.html', books=books)


# ----------------------
# SAVED BOOKS
# ----------------------
@app.route('/saved')
def saved():
    return render_template('saved.html')


# ----------------------
# SETTINGS
# ----------------------
@app.route('/settings')
def settings():
    return render_template('settings.html')


# ----------------------
# ADD BOOK
# ----------------------
@app.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        university = request.form['university']

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO university_books (title, author, year_published, university) VALUES (:1, :2, :3, :4)",
            (title, author, year, university)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash("Book added successfully!", "success")
        return redirect('/')

    return render_template('add.html')


# ----------------------
# EXIT
# ----------------------
@app.route('/exit')
def exit_page():
    session.clear()
    return "You exited the system."


# ----------------------
# RUN APP
# ----------------------
if __name__ == '__main__':
    app.run(debug=True)


'''

from flask import Flask, render_template, request, redirect
import oracledb

app = Flask(__name__)

# --- Local Database (Laptop A) ---
LOCAL_DB_USER = "c##uni1"
LOCAL_DB_PASSWORD = "user1"
LOCAL_DB_DSN = "localhost/FREE"  # Local DB

# --- Remote Database (Laptop B) ---
REMOTE_DB_USER = "c##uni2"
REMOTE_DB_PASSWORD = "user2"
REMOTE_DB_DSN = "192.168.1.11/FREE"  # Remote DB IP

def get_local_connection():
    return oracledb.connect(user=LOCAL_DB_USER, password=LOCAL_DB_PASSWORD, dsn=LOCAL_DB_DSN)

def get_remote_connection():
    return oracledb.connect(user=REMOTE_DB_USER, password=REMOTE_DB_PASSWORD, dsn=REMOTE_DB_DSN)

@app.route('/')
def index():
    search_type = request.args.get("filter")
    keyword = request.args.get("keyword")
    sort = request.args.get("sort")

    # --- Fetch from both databases ---
    local_conn = get_local_connection()
    remote_conn = get_remote_connection()

    local_cursor = local_conn.cursor()
    remote_cursor = remote_conn.cursor()

    # Base query
    query = "SELECT book_id, title, author, year_published, university FROM university_books"
    params = []

    if keyword:
        keyword_param = f"%{keyword.lower()}%"
        if search_type == "university":
            query += " WHERE LOWER(university) LIKE :keyword"
        elif search_type == "author":
            query += " WHERE LOWER(author) LIKE :keyword"
        elif search_type == "title":
            query += " WHERE LOWER(title) LIKE :keyword"
        params = [keyword_param]

    if sort:
        query += f" ORDER BY {sort}"

    local_cursor.execute(query, params)
    remote_cursor.execute(query, params)

    books_local = [{"id": r[0], "title": r[1], "author": r[2], "year": r[3], "university": r[4]} for r in local_cursor]
    books_remote = [{"id": r[0], "title": r[1], "author": r[2], "year": r[3], "university": r[4]} for r in remote_cursor]

    # Combine results
    books = books_local + books_remote

    local_cursor.close()
    remote_cursor.close()
    local_conn.close()
    remote_conn.close()

    return render_template('index.html', books=books)


@app.route('/add', methods=('GET', 'POST'))
def add():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        university = request.form['university']

        # Save to local DB only for simplicity
        conn = get_local_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO university_books (title, author, year_published, university) VALUES (:1, :2, :3, :4)",
            (title, author, year, university)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/')
    return render_template('add.html')


@app.route('/saved')
def saved():
    return render_template('saved.html')


@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route('/settings')
def settings():
    return render_template('settings.html')


@app.route('/exit')
def exit_page():
    return "You exited the system."


if __name__ == '__main__':
    app.run(debug=True)

'''