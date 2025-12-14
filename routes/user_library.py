from flask import Blueprint, render_template, session, redirect, url_for, flash, request, send_file, abort
from dbconnections.dbconnections import get_connection
from datetime import datetime
import io

bp = Blueprint("user_library", __name__, url_prefix="/library")
REMOTE_DB_LINK = "remote_uni"  # DB link for remote database

# ---------------------------
# ADD BOOK TO USER LIBRARY
# ---------------------------
@bp.route("/add/<int:book_id>", methods=["POST"])
def add_to_library(book_id):
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    source = request.form.get("source", "Local").capitalize()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Determine source table
        table_name = "university_books" if source == "Local" else f"university_books@{REMOTE_DB_LINK}"

        # Fetch the entire book record
        cursor.execute(f"""
            SELECT book_id, title, author, university, department, year_published, pdf_file
            FROM {table_name}
            WHERE book_id = :1
        """, (book_id,))
        book = cursor.fetchone()

        if not book:
            flash(f"Book does not exist in {source} database.", "error")
            return redirect(url_for("books.index"))

        # Insert into user_library
        cursor.execute("""
            MERGE INTO user_library ul
            USING (
                SELECT :user_id AS user_id, :book_id AS book_id, :title AS title, :author AS author,
                       :university AS university, :department AS department, :year_published AS year_published,
                       :pdf_file AS pdf_file, :added_at AS added_at, :source AS source
                FROM dual
            ) src
            ON (ul.user_id = src.user_id AND ul.book_id = src.book_id)
            WHEN NOT MATCHED THEN
                INSERT (user_id, book_id, title, author, university, department, year_published, pdf_file, added_at, source)
                VALUES (src.user_id, src.book_id, src.title, src.author, src.university, src.department, src.year_published, src.pdf_file, src.added_at, src.source)
        """, {
            "user_id": user_id,
            "book_id": book[0],
            "title": book[1],
            "author": book[2],
            "university": book[3],
            "department": book[4],
            "year_published": book[5],
            "pdf_file": book[6],
            "added_at": datetime.now(),
            "source": source
        })

        conn.commit()
        flash(f"Book added to your library from {source} database!", "success")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for("books.index"))

# ---------------------------
# VIEW USER'S LIBRARY
# ---------------------------
@bp.route("/my-library")
def my_library():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    local_books = []
    remote_books = []

    conn = get_connection()
    cursor = conn.cursor()

    # Fetch all books for this user from the local table
    cursor.execute("""
        SELECT book_id, title, author, university, department, year_published, source
        FROM user_library
        WHERE user_id = :1
    """, (user_id,))
    
    for row in cursor.fetchall():
        book_data = {
            "book_id": row[0],
            "title": row[1],
            "author": row[2],
            "university": row[3],
            "department": row[4],
            "year_published": row[5],
            "source": (row[6] or "Local").capitalize()
        }

        if book_data["source"].lower() == "local":
            local_books.append(book_data)
        else:
            remote_books.append(book_data)

    cursor.close()
    conn.close()

    return render_template("saved.html", local_books=local_books, remote_books=remote_books)


# ---------------------------
# REMOVE BOOK FROM LIBRARY
# ---------------------------
@bp.route("/remove/<int:book_id>", methods=["POST"])
def remove_from_library(book_id):
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_library WHERE user_id = :1 AND book_id = :2", (user_id, book_id))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Book removed from your library.", "success")
    return redirect(url_for("user_library.my_library"))

# ---------------------------
# VIEW PDF
# ---------------------------
from flask import render_template_string

from flask import render_template_string, send_file, session, redirect, url_for, flash
import io
from dbconnections.dbconnections import get_connection


@bp.route("/pdf/<int:book_id>")
def view_pdf(book_id):
    user_id = session.get("user_id")
    if not user_id:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Get PDF from the local table only
        cursor.execute("""
            SELECT pdf_file, source
            FROM user_library
            WHERE user_id = :1 AND book_id = :2
        """, (user_id, book_id))

        row = cursor.fetchone()
        if not row:
            flash("Book not found in your library.", "error")
            return redirect(url_for("user_library.my_library"))

        pdf_blob, source = row
        if not pdf_blob:
            flash("No PDF available for this book.", "info")
            return redirect(url_for("user_library.my_library"))

        # Read the BLOB
        pdf_bytes = pdf_blob.read() if hasattr(pdf_blob, 'read') else pdf_blob
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            download_name=f"book_{book_id}.pdf"
        )

    except Exception as e:
        flash(f"Cannot fetch PDF: {e}", "error")
        return redirect(url_for("user_library.my_library"))
    finally:
        cursor.close()
        conn.close()




@bp.route("/remote-library")
def remote_library():
    if "user_id" not in session:
        flash("Please login first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]
    remote_books = []

    # Fetch only remote entries from user_library
    conn_local = get_connection()
    cursor_local = conn_local.cursor()
    cursor_local.execute(
        "SELECT book_id, source FROM user_library WHERE user_id = :1 AND UPPER(source) = 'REMOTE'",
        (user_id,)
    )
    entries = cursor_local.fetchall()
    cursor_local.close()
    conn_local.close()

    for book_id, source in entries:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            # Query the remote database via DB link
            cursor.execute(f"""
                SELECT book_id, title, author, university, department, year_published
                FROM university_books@{REMOTE_DB_LINK}
                WHERE book_id = :1
            """, (book_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if row:
                remote_books.append({
                    "book_id": row[0],
                    "title": row[1],
                    "author": row[2],
                    "university": row[3],
                    "department": row[4],
                    "year_published": row[5],
                    "source": "Remote"
                })
        except Exception as e:
            flash(f"Cannot fetch remote book {book_id}: {e}", "error")

    return render_template("remote_saved.html", books=remote_books)

