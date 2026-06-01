from flask import Flask, render_template, request, redirect
import sqlite3
import os
from datetime import datetime, timedelta

print(os.getcwd())
print("AAAAAAAA")
print("AAAAAAAA")
app = Flask(__name__)

def init_db():

    conn = sqlite3.connect("shift.db")

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        time TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]

        conn = sqlite3.connect("shift.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO shifts (name, date, time)
            VALUES (?, ?, ?)
            """,
            (name, date, time)
        )
        conn.commit()
        conn.close()

        return redirect("/")
    today = datetime.today().date()

    two_weeks_later = today + timedelta(days=14)





    conn = sqlite3.connect("shift.db")
    cursor = conn.cursor()
    cursor.execute(
    """
    SELECT id, name, date, time
    FROM shifts
    WHERE date >= ?
    AND date <= ?
    ORDER BY date
    """,
    (str(today), str(two_weeks_later))
)
    shifts = [
        {"id": row[0], "name": row[1], "date": row[2], "time": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return render_template("index.html", shifts=shifts)

@app.route("/edit/<int:id>")
def edit(id):

    conn = sqlite3.connect("shift.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name, date, time FROM shifts WHERE id = ?",
        (id,)
    )

    row = cursor.fetchone()

    conn.close()

    if row is None:
        return redirect("/")

    shift = {
        "id": row[0],
        "name": row[1],
        "date": row[2],
        "time": row[3]
    }

    return render_template(
        "edit.html",
        shift=shift
    )

@app.route("/update/<int:id>", methods=["POST"])
def update(id):

    name = request.form["name"]
    date = request.form["date"]
    time = request.form["time"]

    conn = sqlite3.connect("shift.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE shifts
        SET name = ?,
            date = ?,
            time = ?
        WHERE id = ?
        """,
        (name, date, time, id)
    )

    conn.commit()
    conn.close()

    return redirect("/")
@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    conn = sqlite3.connect("shift.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shifts WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True, port=5001)