from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file, abort
from dbconnections.dbconnections import get_connection
import io

bp = Blueprint("user_library", __name__, url_prefix="/library")


# -------------------------------------------------------
# ADD BOOK TO USER LIBRARY
# -------------------------------------------------------
@bp.route("/add/<int:book_id>", methods=["POST"])
def add_to_library(book_id):
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Check if already in library
        cursor.execute("""
            SELECT COUNT(*) 
            FROM user_library 
            WHERE user_id = :1 AND book_id = :2
        """, (user_id, book_id))

        exists = cursor.fetchone()[0]

        if exists > 0:
            flash("Book is already in your library.", "info")
        else:
            cursor.execute("""
                INSERT INTO user_library (user_id, book_id) 
                VALUES (:1, :2)
            """, (user_id, book_id))
            conn.commit()
            flash("Book added to your library!", "success")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("books.index"))



# -------------------------------------------------------
# VIEW USER'S PERSONAL LIBRARY
# -------------------------------------------------------
@bp.route("/my-library")
def my_library():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 
                ub.book_id,
                ub.title,
                ub.author,
                ub.university,
                ub.department,
                ub.year_published,
                ub.pdf_file
            FROM university_books ub
            JOIN user_library ul 
                ON ub.book_id = ul.book_id
            WHERE ul.user_id = :1
            ORDER BY ub.title
        """, (user_id,))

        rows = cursor.fetchall()

        # Convert to dicts for Jinja template
        books = [
            {
                "book_id": row[0],
                "title": row[1],
                "author": row[2],
                "university": row[3],
                "department": row[4],
                "year_published": row[5],
                "pdf_file": row[6]
            }
            for row in rows
        ]

    finally:
        cursor.close()
        conn.close()

    return render_template("saved.html", books=books)



# -------------------------------------------------------
# REMOVE BOOK FROM LIBRARY
# -------------------------------------------------------
@bp.route("/remove/<int:book_id>", methods=["POST"])
def remove_from_library(book_id):
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            DELETE FROM user_library 
            WHERE user_id = :1 AND book_id = :2
        """, (user_id, book_id))

        conn.commit()
        flash("Book removed from your library.", "success")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("user_library.my_library"))



# -------------------------------------------------------
# VIEW PDF (Oracle LOB / BLOB SAFE READER)
# -------------------------------------------------------
@bp.route("/pdf/<int:book_id>")
def view_pdf(book_id):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT pdf_file
            FROM university_books
            WHERE book_id = :1
        """, (book_id,))
        row = cursor.fetchone()

        if not row or not row[0]:
            abort(404)

        pdf_lob = row[0]

        # Oracle LOB → must use .read()
        pdf_bytes = pdf_lob.read()

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"book_{book_id}.pdf"
        )

    finally:
        cursor.close()
        conn.close()
