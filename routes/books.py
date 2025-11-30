from flask import Blueprint, render_template, request, flash, redirect, url_for
from dbconnections.dbconnections import get_connection

bp = Blueprint("books", __name__)

@bp.route("/")
def index():
    search_type = request.args.get("filter")
    keyword = request.args.get("keyword")
    sort = request.args.get("sort")

    conn = get_connection()
    cursor = conn.cursor()
    
    # Select all fields except availability
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
        # Safety: allow only specific sort columns
        allowed_sort = ["book_id", "title", "author", "university", "department", "year_published"]
        if sort in allowed_sort:
            query += f" ORDER BY {sort}"

    cursor.execute(query, params)
    
    # Return all fields in dictionary
    books = [
        {
            "book_id": r[0],
            "title": r[1],
            "author": r[2],
            "university": r[3],
            "department": r[4],
            "year_published": r[5]
        } for r in cursor
    ]

    cursor.close()
    conn.close()
    return render_template("index.html", books=books)

@bp.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        year = request.form["year"]
        university = request.form["university"]
        department = request.form["department"]

        conn = get_connection()
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
        flash("Book added successfully!", "success")
        return redirect(url_for("books.index"))

    return render_template("add.html")

@bp.route("/saved")
def saved():
    return render_template("saved.html")
