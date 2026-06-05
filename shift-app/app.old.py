from datetime import datetime, timedelta
import sqlite3

from flask import Flask, redirect, render_template, request, session

DATABASE = "shift.db"

app = Flask(__name__)
app.secret_key = "shift_app_secret"


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            date TEXT,
            time TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_db_connection():
    return sqlite3.connect(DATABASE)


init_db()


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO shifts (name, date, time) VALUES (?, ?, ?)",
            (name, date, time),
        )
        conn.commit()
        conn.close()

        return redirect("/")

    today = datetime.today().date()
    two_weeks_later = today + timedelta(days=14)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, name, date, time
        FROM shifts
        WHERE date >= ?
          AND date <= ?
        ORDER BY date
        """,
        (str(today), str(two_weeks_later)),
    )
    shifts = [
        {"id": row[0], "name": row[1], "date": row[2], "time": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return render_template("index.html", shifts=shifts)


@app.route("/edit/<int:id>")
def edit(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, date, time FROM shifts WHERE id = ?",
        (id,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return redirect("/")

    shift = {
        "id": row[0],
        "name": row[1],
        "date": row[2],
        "time": row[3],
    }

    return render_template("edit.html", shift=shift)


@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    name = request.form["name"]
    date = request.form["date"]
    time = request.form["time"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE shifts SET name = ?, date = ?, time = ? WHERE id = ?",
        (name, date, time, id),
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shifts WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, "user"),
        )
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username,),
        )
        user = cursor.fetchone()
        conn.close()

        if user is not None and user[2] == password:
            session["user_id"] = user[0]
            return redirect("/")

        return "ログイン失敗"

    return render_template("login.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
