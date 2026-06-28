import os
import secrets
import shutil
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, redirect, render_template, request, session
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "shift.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "dev_secret_key")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

csrf = CSRFProtect(app)

def init_db():
    """
    アプリ起動時に必要なテーブルを作成する関数。
    初回起動時は管理者アカウントも自動作成する。
    """
    with sqlite3.connect(DATABASE) as conn:
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

        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            """,
            ("admin",)
        )

        admin_user = cursor.fetchone()

        if admin_user is None:
            admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
            hashed_password = generate_password_hash(admin_password)

            cursor.execute(
                """
                INSERT INTO users (
                    username,
                    password,
                    role
                )
                VALUES (?, ?, ?)
                """,
                ("admin", hashed_password, "admin")
            )

        conn.commit()

def get_db_connection():
    """
    データベース接続を返す共通関数
    """
    return sqlite3.connect(DATABASE)


init_db()


def is_admin():
    """
    ログイン中のユーザーが管理者かどうかを判定する
    """
    user_id = session.get("user_id")

    if user_id is None:
        return False

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role FROM users WHERE id = ?",
            (user_id,),
        )
        user = cursor.fetchone()

    if user is None:
        return False

    return user[0] == "admin"
@app.route("/", methods=["GET", "POST"])
def home():
    """
    トップページの処理
    GET：ログイン中ユーザーのシフト一覧を表示
    POST：入力されたシフトを登録
    """
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
    # DB接続を終了
    conn.close()
     # フォームからシフトが送信された場合
    if request.method == "POST":
        # フォームに入力された値を取得
        name = request.form["name"]
        date = request.form["date"]
        time = request.form["time"]
        end_time = request.form["end_time"]
         # ログイン中のユーザーIDを取得
        user_id = session["user_id"]
         # データベースへ接続
        conn = get_db_connection()
        cursor = conn.cursor()
         # 入力されたシフト情報を登録
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
         # 変更内容を保存
        conn.commit()
         # DB接続を終了
        conn.close()
        # 登録後はトップページへ戻る
        return redirect("/")
     # 今日の日付を取得
    today = datetime.today().date()
    # 今日から2週間後の日付を計算
    two_weeks_later = today + timedelta(days=14)
     # データベースへ接続
    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ取得
     # 今日から2週間後までのシフトを日付順で表示する
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
     # 取得したシフト情報をHTMLで使いやすい辞書形式に変換
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
     # DB接続を終了
    conn.close()
    # index.htmlに必要なデータを渡して表示
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
    # データベースへ接続
    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザーのシフトだけ取得
    # user_idも条件にすることで他人のシフトを編集できないようにする
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
    # シフトが存在しない場合はトップページへ戻る
    if row is None:
        return redirect("/")
    # HTMLで扱いやすい辞書形式へ変換
    shift = {
        "id": row[0],
        "name": row[1],
        "date": row[2],
        "time": row[3],
        "end_time": row[4]
    }
    # 編集画面を表示
    return render_template("edit.html", shift=shift)


@app.route("/update/<int:id>", methods=["POST"])
def update(id):
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")
    # フォームから送信された値を取得
    name = request.form["name"]
    date = request.form["date"]
    time = request.form["time"]
    end_time = request.form["end_time"]
    # データベースへ接続
    conn = get_db_connection()
    cursor = conn.cursor()
    # ログイン中のユーザー本人のシフトだけ更新可能
    # user_idも条件にすることで本人以外は更新できない
    cursor.execute(
        """
        UPDATE shifts
        SET name = ?, date = ?, time = ?, end_time = ?
        WHERE id = ?
          AND user_id = ?
        """,
        (name, date, time, end_time, id, session["user_id"]),
    )
    # 更新内容を保存
    conn.commit()
    # DB接続を終了
    conn.close()
    # 更新後はトップページへ戻る
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
    # 削除後はトップページへ戻る
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    # ログインしていない場合はログイン画面へ移動
    if "user_id" not in session:
        return redirect("/login")

    # 管理者でない場合はトップページへ移動
    if not is_admin():
        return redirect("/")

    # ユーザー登録フォームが送信された場合
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

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

            return redirect("/admin")

        except sqlite3.IntegrityError:
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

    # ログイン失敗回数が5回以上ならログインを止める
    if session.get("login_failed_count", 0) >= 5:
        return render_template(
            "login.html",
            error="ログイン失敗が多すぎます。しばらくしてから再度お試しください。"
        )

    # ログインフォームが送信された場合
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        # 入力されたユーザー名に一致するユーザーを検索
        cursor.execute(
            "SELECT id, username, password FROM users WHERE username = ?",
            (username,),
        )
        user = cursor.fetchone()
        conn.close()

        # ハッシュ化されたパスワードを検証
        if user is not None and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session.pop("login_failed_count", None)
            return redirect("/")

        # ログイン失敗回数を1増やす
        session["login_failed_count"] = session.get("login_failed_count", 0) + 1

        # ログイン失敗時はログイン画面を再表示
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
    # 日付検索で指定された日付を取得
    selected_date = request.args.get("date")

    conn = get_db_connection()
    cursor = conn.cursor()
    # 全ユーザーのシフトを取得
    if selected_date:
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
            WHERE shifts.date = ?
              AND NOT EXISTS (
                  SELECT 1
                  FROM confirmed_shifts
                WHERE confirmed_shifts.user_id = shifts.user_id
                    AND confirmed_shifts.date = shifts.date
                    AND confirmed_shifts.time = shifts.time
                    AND confirmed_shifts.end_time = shifts.end_time
            )
            ORDER BY shifts.date
            """,
            (selected_date,)
        )
    else:
        # 日付指定がない場合は全ての未確定シフトを取得
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
            WHERE NOT EXISTS (
                SELECT 1
                FROM confirmed_shifts
                WHERE confirmed_shifts.user_id = shifts.user_id
                  AND confirmed_shifts.date = shifts.date
                  AND confirmed_shifts.time = shifts.time
                  AND confirmed_shifts.end_time = shifts.end_time
            )
            ORDER BY shifts.date
            """
        )
        # HTMLで扱いやすい辞書形式へ変換
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
    # 管理者画面を表示
    return render_template(
        "admin.html",
        shifts=shifts,
        selected_date=selected_date,
    )
    
@app.route("/users")
def users():

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, username, role
        FROM users
        ORDER BY id
        """
    )

    users = [
        {
            "id": row[0],
            "username": row[1],
            "role": row[2],
        }
        for row in cursor.fetchall()
    ]

    conn.close()

    return render_template("users.html", users=users)

@app.route("/delete_user_confirm/<int:user_id>")
def delete_user_confirm(user_id):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, role FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()
    conn.close()

    if user is None:
        return redirect("/users")

    if user[2] == "admin":
        return redirect("/users")

    user_data = {
        "id": user[0],
        "username": user[1],
        "role": user[2],
    }

    return render_template("delete_user_confirm.html", user=user_data)

@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id = ?",
        (user_id,)
    )

    user = cursor.fetchone()

    if user is None:
        conn.close()
        return redirect("/users")

    if user[0] == "admin":
        conn.close()
        return redirect("/users")

    cursor.execute(
        "DELETE FROM shifts WHERE user_id = ?",
        (user_id,)
    )

    cursor.execute(
        "DELETE FROM confirmed_shifts WHERE user_id = ?",
        (user_id,)
    )

    cursor.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/users")
@app.route("/logout")
def logout():

    # セッション情報を削除してログアウト
    session.clear()

    return redirect("/login")

@app.route("/backup")
def backup_db():
    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    # データバックアップを作成するためのディレクトリを作成
    os.makedirs(BACKUP_DIR, exist_ok=True)

    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"shift_backup_{now}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    shutil.copy(DATABASE, backup_path)

    return f"バックアップを作成しました: {backup_filename}"

@app.route("/backup_list")
def backup_list():

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    files = os.listdir(BACKUP_DIR)

    files.sort(reverse=True)

    return render_template(
        "backup_list.html",
        files=files
    )
    
@app.route("/restore_confirm/<filename>")
def restore_confirm(filename):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    return render_template(
        "restore_confirm.html",
        filename=filename
    )
    
@app.route("/restore_backup/<filename>", methods=["POST"])
def restore_backup(filename):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_path):
        return redirect("/backup_list")

    before_restore_filename = "before_restore_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".db"
    before_restore_path = os.path.join(BACKUP_DIR, before_restore_filename)

    shutil.copy(DATABASE, before_restore_path)

    shutil.copy(backup_path, DATABASE)

    return redirect("/backup_list")

@app.route("/delete_backup/<filename>", methods=["POST"])
def delete_backup(filename):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    backup_path = os.path.join(BACKUP_DIR, filename)

    if not os.path.exists(backup_path):
        return redirect("/backup_list")

    os.remove(backup_path)

    return redirect("/backup_list")

@app.route("/confirm_shift/<int:shift_id>")
def confirm_shift(shift_id):
    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()
    # 指定されたシフトIDの情報を取得
    # usersテーブルと結合してユーザー名も取得する
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

    date = request.form["date"]
    time = request.form["time"]
    end_time = request.form["end_time"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT shifts.user_id,
               users.username
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
            date,
            time,
            end_time
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
            date,
            time,
            end_time
        ),
    )
    
    cursor.execute(
        """
        DELETE FROM shifts
        WHERE id = ?
        """,
        (shift_id,)
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
    # 確定済みシフトを日付順で取得
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
    # ログイン中のユーザーの確定済みシフトのみ取得
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

@app.route("/unconfirm_shift/<int:id>", methods=["POST"])
def unconfirm_shift(id):

    if "user_id" not in session:
        return redirect("/login")

    if not is_admin():
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()
    # 指定された確定済みシフトを削除
    # 確定取り消しの役割を持つ
    cursor.execute(
        """
        DELETE FROM confirmed_shifts
        WHERE id = ?
        """,
        (id,)
    )

    conn.commit()
    conn.close()

    return redirect("/confirmed_shifts")

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500



if __name__ == "__main__":
    app.run(debug=True, port=5001)
