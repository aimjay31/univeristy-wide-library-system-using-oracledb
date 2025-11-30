from flask import Blueprint, render_template, request, flash, redirect, url_for, session, send_file
from dbconnections.dbconnections import get_connection
from io import BytesIO

bp = Blueprint("librarian", __name__, url_prefix="/librarian")

# ---------------------------
# Helper
# ---------------------------
def require_librarian():
    if session.get("role") != "librarian":
        flash("Access denied. Librarians only.", "error")
        return False
    return True


# ---------------------------
# Dashboard
# ---------------------------
@bp.route("/")
def dashboard():
    if not require_librarian():
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        # Show ALL books, not only those uploaded by the librarian
        cursor.execute("""
            SELECT book_id, title, author, university, department, year_published
            FROM university_books
            ORDER BY title
        """)
        books = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("librarian/dashboard.html", books=books)


# ---------------------------
# Add Book
# ---------------------------
@bp.route("/add", methods=["GET", "POST"])
def add_book():
    if not require_librarian():
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        university = request.form.get("university", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year_published", "").strip()
        pdf_file = request.files.get("pdf_file")
        pdf_bytes = pdf_file.read() if pdf_file and pdf_file.filename else None

        # Validation
        if not (title and author and university and department and year and pdf_bytes):
            flash("All fields including PDF are required.", "error")
            return render_template("librarian/insert.html")

        try:
            year_int = int(year)
        except ValueError:
            flash("Year must be a number.", "error")
            return render_template("librarian/insert.html")

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO university_books
                (title, author, university, department, year_published, pdf_file, uploaded_by)
                VALUES (:1, :2, :3, :4, :5, :6, :7)
            """, (title, author, university, department, year_int, pdf_bytes, session.get("user_id")))
            conn.commit()
            flash("Book added successfully!", "success")
            return redirect(url_for("librarian.dashboard"))
        except Exception as e:
            conn.rollback()
            flash("Error adding book: " + str(e), "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("librarian/insert.html")


# ---------------------------
# View PDF
# ---------------------------
@bp.route("/view/<int:book_id>")
def view_book(book_id):
    if not require_librarian():
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT title, pdf_file 
            FROM university_books 
            WHERE book_id=:1
        """, (book_id,))
        book = cursor.fetchone()
        if not book or not book[1]:
            flash("Book PDF not found.", "error")
            return redirect(url_for("librarian.dashboard"))

        # Convert Oracle LOB to bytes
        pdf_bytes = book[1].read()  # <--- Important!

        return send_file(
            BytesIO(pdf_bytes),
            download_name=f"{book[0]}.pdf",
            mimetype="application/pdf"
        )
    finally:
        cursor.close()
        conn.close()


# ---------------------------
# Delete Book
# ---------------------------
@bp.route("/delete/<int:book_id>", methods=["POST"])
def delete_book(book_id):
    if not require_librarian():
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM university_books WHERE book_id=:1", (book_id,))
        conn.commit()
        flash("Book deleted successfully.", "success")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("librarian.dashboard"))




@bp.route("/search", methods=["GET"])
def search():
    if not require_librarian():
        return redirect(url_for("auth.login"))

    keyword = request.args.get("keyword", "").strip()
    filter_by = request.args.get("filter", "title")

    if filter_by not in ["title", "author", "university", "department"]:
        filter_by = "title"

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = f"""
            SELECT book_id, title, author, university, department, year_published
            FROM university_books
            WHERE 1=1
        """
        params = {}

        if keyword:
            query += f" AND LOWER({filter_by}) LIKE :keyword"
            params["keyword"] = f"%{keyword.lower()}%"

        query += " ORDER BY title"
        cursor.execute(query, params)
        books = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return render_template("librarian/dashboard.html", books=books, keyword=keyword, filter_by=filter_by)



# ---------------------------
# Edit Book
# ---------------------------
@bp.route("/edit/<int:book_id>", methods=["GET", "POST"])
def edit_book(book_id):
    if not require_librarian():
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        # Get form values
        title = request.form.get("title", "").strip()
        author = request.form.get("author", "").strip()
        university = request.form.get("university", "").strip()
        department = request.form.get("department", "").strip()
        year = request.form.get("year_published", "").strip()
        pdf_file = request.files.get("pdf_file")
        pdf_bytes = pdf_file.read() if pdf_file and pdf_file.filename else None

        try:
            year_int = int(year)
        except ValueError:
            flash("Year must be a number.", "error")
            return redirect(url_for("librarian.edit_book", book_id=book_id))

        try:
            if pdf_bytes:
                cursor.execute("""
                    UPDATE university_books
                    SET title=:1, author=:2, university=:3, department=:4, year_published=:5, pdf_file=:6
                    WHERE book_id=:7
                """, (title, author, university, department, year_int, pdf_bytes, book_id))
            else:
                cursor.execute("""
                    UPDATE university_books
                    SET title=:1, author=:2, university=:3, department=:4, year_published=:5
                    WHERE book_id=:6
                """, (title, author, university, department, year_int, book_id))

            conn.commit()
            flash("Book updated successfully!", "success")
            return redirect(url_for("librarian.dashboard"))
        except Exception as e:
            conn.rollback()
            flash("Error updating book: " + str(e), "error")
        finally:
            cursor.close()
            conn.close()

    # GET request → fetch existing book data
    try:
        cursor.execute("""
            SELECT title, author, university, department, year_published
            FROM university_books
            WHERE book_id=:1
        """, (book_id,))
        book = cursor.fetchone()
        if not book:
            flash("Book not found.", "error")
            return redirect(url_for("librarian.dashboard"))

        book_data = {
            "title": book[0],
            "author": book[1],
            "university": book[2],
            "department": book[3],
            "year_published": book[4]
        }

    finally:
        cursor.close()
        conn.close()

    return render_template("librarian/edit.html", book=book_data)

