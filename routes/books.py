from flask import Blueprint, render_template, request, flash, redirect, url_for
from dbconnections.dbconnections import get_connection, get_remote_connection

bp = Blueprint("books", __name__)

def query_books(conn, source_name, search_type=None, keyword=None, sort=None):
    """
    Execute book query on a given connection and return list of dictionaries.
    Adds a 'source' field to indicate local or remote DB.
    """
    cursor = conn.cursor()
    query = """
        SELECT book_id, title, author, university, department, year_published
        FROM university_books
    """
    params = []

    if keyword:
        keyword_param = f"%{keyword.lower()}%"
        if search_type == "university":
            query += " WHERE LOWER(university) LIKE :keyword"
        elif search_type == "author":
            query += " WHERE LOWER(author) LIKE :keyword"
        elif search_type == "title":
            query += " WHERE LOWER(title) LIKE :keyword"
        elif search_type == "department":
            query += " WHERE LOWER(department) LIKE :keyword"
        elif search_type == "year_published":
            query += " WHERE TO_CHAR(year_published) LIKE :keyword"
        params = [keyword_param]

    if sort:
        allowed_sort = ["book_id", "title", "author", "university", "department", "year_published"]
        if sort in allowed_sort:
            query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    books = [
        {
            "book_id": r[0],
            "title": r[1],
            "author": r[2],
            "university": r[3],
            "department": r[4],
            "year_published": r[5],
            "source": source_name  # <--- add this
        }
        for r in cursor
    ]
    cursor.close()
    return books

@bp.route("/")
def index():
    search_type = request.args.get("filter")
    keyword = request.args.get("keyword")
    sort = request.args.get("sort")
    db_source = request.args.get("db_source", "local")  # local, remote, all

    all_books = []

    # Query local DB
    if db_source in ["local", "all"]:
        try:
            conn = get_connection()
            all_books.extend(query_books(conn, source_name="Local", search_type=search_type, keyword=keyword, sort=sort))
            conn.close()
        except Exception as e:
            flash(f"Failed to fetch local books: {e}", "error")

    # Query remote DB
    if db_source in ["remote", "all"]:
        try:
            conn = get_remote_connection()
            all_books.extend(query_books(conn, source_name="Remote", search_type=search_type, keyword=keyword, sort=sort))
            conn.close()
        except Exception as e:
            flash(f"Failed to fetch remote books: {e}", "error")

    return render_template("index.html", books=all_books, db_source=db_source)



@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        university = request.form["university"]
        department = request.form["department"]
        db_source = request.form.get("db_source", "local")  # where to add

        conn = get_connection() if db_source == "local" else get_remote_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO university_books (title, author, year_published, university, department)
            VALUES (:1, :2, :3, :4, :5)
            """,
            (title, author, year, university, department)
        )
        conn.commit()
        cursor.close()
        conn.close()
        flash(f"Book added successfully to {db_source} database!", "success")
        return redirect(url_for("books.index"))

    return render_template("add.html")


from flask import send_file
from io import BytesIO

@bp.route("/view/<int:book_id>")
def view(book_id):
    source = request.args.get("source", "local")  # local | remote
    conn = get_connection() if source == "local" else get_remote_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT pdf_file, title
            FROM university_books
            WHERE book_id = :1
            """,
            (book_id,)
        )

        row = cursor.fetchone()

        if not row or not row[0]:
            flash("PDF not found.", "error")
            return redirect(url_for("books.index"))

        pdf_blob = row[0].read()   # IMPORTANT for Oracle BLOB
        title = row[1]

        return send_file(
            BytesIO(pdf_blob),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=f"{title}.pdf"
        )

    finally:
        cursor.close()
        conn.close()


