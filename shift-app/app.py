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
            user_id INTEGER,
            name TEXT,
            date TEXT,
            time TEXT,
            end_time TEXT
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

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS confirmed_shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            date TEXT,
            time TEXT,
            end_time TEXT
        )
        """
    )

    conn.commit()
    conn.close()


def get_db_connection():
    return sqlite3.connect(DATABASE)


init_db()





def is_admin():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id = ?",
        (session["user_id"],),
    )

    user = cursor.fetchone()

    conn.close()

    return user[0] == "admin"


@app.route("/", methods=["GET", "POST"])
def home():
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    # ログイン中のユーザー情報を取得
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role FROM users WHERE id = ?",
        (session["user_id"],),
    )
    user = cursor.fetchone()
    conn.close()

    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]
        end_time = request.form["end_time"]

        user_id = session["user_id"]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO shifts (
                user_id,
                name,
                date,
                time,
                end_time
        )
    VALUES (?, ?, ?, ?, ?)
    """,
    (user_id, name, date, time, end_time),
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
        SELECT id, name, date, time, end_time
        FROM shifts
        WHERE user_id = ?
          AND date >= ?
          AND date <= ?
        ORDER BY date
        """,
        (session["user_id"], str(today), str(two_weeks_later)),
    )
    shifts = [
        {
            "id": row[0],
            "name": row[1],
            "date": row[2],
            "time": row[3],
        "end_time": row[4]
        }
        for row in cursor.fetchall()
    ]
    conn.close()

    return render_template(
        "index.html",
        shifts=shifts,
        username=user[0],
        is_admin_user=(user[1] == "admin"),
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
        SELECT id, name, date, time, end_time
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
        "end_time": row[4]
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
    end_time = request.form["end_time"]

    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ更新可能
    cursor.execute(
        """
        UPDATE shifts
        SET name = ?, date = ?, time = ?, end_time = ?
        WHERE id = ?
          AND user_id = ?
        """,
        (name, date, time, end_time, id, session["user_id"]),
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
     # 既にログインしている場合はトップページへ移動
    if "user_id" in session:
        return redirect("/")

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

            # 登録したユーザーのIDをセッションへ保存
            session["user_id"] = cursor.lastrowid

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
    # 既にログインしている場合はトップページへ移動
    if "user_id" in session:
        return redirect("/")

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

@app.route("/manager")
def manager():
    # ログインしていない場合
    if "user_id" not in session:
        return redirect("/login")
    # 管理者でない場合
    if not is_admin():
        return redirect("/")

    return "管理者ページ"

@app.route("/admin")
def admin():

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()
    # 全ユーザーのシフトを取得
    cursor.execute(
        """
        SELECT
            shifts.id,
            users.username,
            shifts.date,
            shifts.time,
            shifts.end_time
        FROM shifts
        JOIN users
        ON shifts.user_id = users.id
        ORDER BY shifts.date
        """
    )

    shifts = [
        {
            "id": row[0],
            "username": row[1],
            "date": row[2],
            "time": row[3],
            "end_time": row[4],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return render_template(
        "admin.html",
        shifts=shifts,
    )
@app.route("/logout")
def logout():

    # セッション情報を削除してログアウト
    session.clear()

    return redirect("/login")

@app.route("/confirm_shift/<int:shift_id>")
def confirm_shift(shift_id):
    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT shifts.id,
               users.username,
               shifts.date,
               shifts.time,
               shifts.end_time
        FROM shifts
        JOIN users ON shifts.user_id = users.id
        WHERE shifts.id = ?
        """,
        (shift_id,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return redirect("/admin")

    shift = {
        "id": row[0],
        "username": row[1],
        "date": row[2],
        "time": row[3],
        "end_time": row[4],
    }

    return render_template("confirm_shift.html", shift=shift)

@app.route("/confirm_shift/<int:shift_id>", methods=["POST"])
def confirm_shift_post(shift_id):
    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT shifts.user_id,
               users.username,
               shifts.date,
               shifts.time,
               shifts.end_time
        FROM shifts
        JOIN users
        ON shifts.user_id = users.id
        WHERE shifts.id = ?
        """,
        (shift_id,)
    )

    shift = cursor.fetchone()

    if shift is None:
        conn.close()
        return redirect("/admin")
    cursor.execute(
    """
        SELECT COUNT(*)
        FROM confirmed_shifts
        WHERE user_id = ?
          AND date = ?
          AND time = ?
          AND end_time = ?
        """,
        (
            shift[0],
            shift[2],
            shift[3],
            shift[4]
        )
    )

    result = cursor.fetchone()
    
    if result[0] > 0:
        conn.close()
        return redirect("/confirmed_shifts")

    cursor.execute(
        """
        INSERT INTO confirmed_shifts (
            user_id,
            username,
            date,
            time,
        end_time
    )
    VALUES (?, ?, ?, ?, ?)
        """,
        (
            shift[0],
            shift[1],
            shift[2],
            shift[3],
            shift[4]
        ),
    )

    conn.commit()
    conn.close()

    return redirect("/admin")

@app.route("/confirmed_shifts")
def confirmed_shifts():
    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, user_id, username, date, time, end_time
        FROM confirmed_shifts
        ORDER BY date
        """
    )

    shifts = [
    {
        "id": row[0],
        "user_id": row[1],
        "username": row[2],
        "date": row[3],
        "time": row[4],
        "end_time": row[5],
    }
    for row in cursor.fetchall()
]

    conn.close()

    return render_template("confirmed_shifts.html", shifts=shifts)

@app.route("/my_confirmed_shifts")
def my_confirmed_shifts():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, date, time, end_time
        FROM confirmed_shifts
        WHERE user_id = ?
        ORDER BY date
        """,
        (session["user_id"],)
    )

    shifts = [
        {
            "id": row[0],
            "username": row[1],
            "date": row[2],
            "time": row[3],
            "end_time": row[4],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return render_template("my_confirmed_shifts.html", shifts=shifts)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
