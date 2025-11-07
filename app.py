from flask import Flask, render_template, request, redirect
import oracledb

app = Flask(__name__)

DB_USER = "c##uni1"
DB_PASSWORD = "user"
DB_DSN = "localhost/FREE"

def get_connection():
    return oracledb.connect(user=DB_USER, password=DB_PASSWORD, dsn=DB_DSN)

@app.route('/')
def index():
    search_type = request.args.get("filter")
    keyword = request.args.get("keyword")
    sort = request.args.get("sort")

    conn = get_connection()
    cursor = conn.cursor()

    # Base query
    query = "SELECT book_id, title, author, year_published, university FROM university_books"
    params = []

    # Searching
    if keyword:
        if search_type == "university":
            query += " WHERE LOWER(university) LIKE :keyword"
        elif search_type == "author":
            query += " WHERE LOWER(author) LIKE :keyword"
        elif search_type == "title":
            query += " WHERE LOWER(title) LIKE :keyword"
        params = [f"%{keyword.lower()}%"]

    # Sorting
    if sort:
        query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    books = [{"id": r[0], "title": r[1], "author": r[2], "year": r[3], "university": r[4]} for r in cursor]

    cursor.close()
    conn.close()

    return render_template('index.html', books=books)


@app.route('/saved')
def saved():
    return render_template('saved.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/settings')
def settings():
    return render_template('settings.html')

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
        return redirect('/')
    return render_template('add.html')

@app.route('/exit')
def exit_page():
    return "You exited the system."

if __name__ == '__main__':
    app.run(debug=True)
