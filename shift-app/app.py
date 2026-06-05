from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
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

            -- このシフトを登録したユーザーID
            user_id INTEGER,

            name TEXT,
            date TEXT,
            time TEXT
        )
        """,
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
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    # ログイン中のユーザー情報を取得
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    conn.close()

    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]

        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO shifts (user_id, name, date, time) VALUES (?, ?, ?, ?)",
            (user_id, name, date, time),
        )
        conn.commit()
        conn.close()

        return redirect("/")

    today = datetime.today().date()
    two_weeks_later = today + timedelta(days=14)

    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ取得
    cursor.execute(
        """
        SELECT id, name, date, time
        FROM shifts
        WHERE user_id = ?
          AND date >= ?
          AND date <= ?
        ORDER BY date
        """,
        (session["user_id"], str(today), str(two_weeks_later)),
    )
    shifts = [
        {"id": row[0], "name": row[1], "date": row[2], "time": row[3]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return render_template(
        "index.html",
        shifts=shifts,
        username=user[0],
    )


@app.route("/edit/<int:id>")
def edit(id):
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザーのシフトだけ取得
    cursor.execute(
        """
        SELECT id, name, date, time
        FROM shifts
        WHERE id = ?
          AND user_id = ?
        """,
        (id, session["user_id"]),
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
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    name = request.form["name"]
    date = request.form["date"]
    time = request.form["time"]

    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ更新可能
    cursor.execute(
        """
        UPDATE shifts
        SET name = ?, date = ?, time = ?
        WHERE id = ?
          AND user_id = ?
        """,
        (name, date, time, id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id):
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ削除可能
    cursor.execute(
        """
        DELETE FROM shifts
        WHERE id = ?
          AND user_id = ?
        """,
        (id, session["user_id"]),
    )
    conn.commit()
    conn.close()

    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        # パスワードをハッシュ化して保存
        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed_password, "user"),
            )

            conn.commit()
            conn.close()

            return redirect("/")
        # username の UNIQUE 制約に違反した場合
        except sqlite3.IntegrityError:
            # DB接続を閉じる
            conn.close()

            return render_template(
                "register.html",
                error="そのユーザー名は既に使用されています",
            )

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

        # ハッシュ化されたパスワードを検証
        if user is not None and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            return redirect("/")

        # ログイン失敗時はログイン画面を再表示
        # errorをHTMLへ渡して画面に表示する
        return render_template(
    "login.html",
    error="ユーザー名またはパスワードが違います"
)

    return render_template("login.html")

@app.route("/logout")
def logout():

    # セッション情報を削除してログアウト
    session.clear()

    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
