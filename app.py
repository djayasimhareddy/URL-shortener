import sqlite3
import string
import random
import re
from flask import Flask, render_template, request, redirect, session, url_for, abort

app = Flask(__name__)
app.secret_key = "simple_secret_key_123"

DB_NAME = "database.db"



def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS urls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original_url TEXT NOT NULL,
            short_code TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def generate_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))


def is_valid_url(url):
    pattern = re.compile(
        r'^(https?:\/\/)'
        r'([\w\-]+\.)+[\w\-]+'
        r'(\/[\w\-._~:\/?#[\]@!$&\'()*+,;=%]*)?$'
    )
    return re.match(pattern, url) is not None


def generate_unique_code():
    conn = get_db()
    while True:
        code = generate_code()
        row = conn.execute("SELECT id FROM urls WHERE short_code = ?", (code,)).fetchone()
        if row is None:
            conn.close()
            return code




@app.route("/", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/dashboard")

    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect("/dashboard")
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if len(username) < 5 or len(username) > 9:
            error = "Username must be 5 to 9 characters long"
        else:
            conn = get_db()
            existing = conn.execute(
                "SELECT id FROM users WHERE username=?",
                (username,)
            ).fetchone()

            if existing:
                error = "This username already exists"
            else:
                conn.execute(
                    "INSERT INTO users (username, password) VALUES (?, ?)",
                    (username, password)
                )
                conn.commit()
                conn.close()
                return redirect("/")

    return render_template("signup.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")




@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    short_url = None
    error = None

    if request.method == "POST":
        original_url = request.form["original_url"]

        if not is_valid_url(original_url):
            error = "Enter valid URL including http:// or https://"
        else:
            conn = get_db()

            row = conn.execute(
                "SELECT short_code FROM urls WHERE original_url=? AND user_id=?",
                (original_url, session["user_id"])
            ).fetchone()

            if row:
                short_code = row["short_code"]
            else:
                short_code = generate_unique_code()
                conn.execute(
                    "INSERT INTO urls (original_url, short_code, user_id) VALUES (?, ?, ?)",
                    (original_url, short_code, session["user_id"])
                )
                conn.commit()

            conn.close()
            short_url = request.host_url + short_code

    conn = get_db()
    urls = conn.execute(
        "SELECT * FROM urls WHERE user_id=? ORDER BY id DESC",
        (session["user_id"],)
    ).fetchall()
    conn.close()

    return render_template("dashboard.html", short_url=short_url, urls=urls, error=error, username=session["username"])




@app.route("/<code>")
def open_short_url(code):
    conn = get_db()
    row = conn.execute(
        "SELECT original_url FROM urls WHERE short_code=?",
        (code,)
    ).fetchone()
    conn.close()

    if row is None:
        abort(404)

    return redirect(row["original_url"])




if __name__ == "__main__":
    init_db()
    app.run(debug=True)
