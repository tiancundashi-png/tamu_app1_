from flask_wtf.csrf import CSRFProtect
# 日付や日時計算を行うためのライブラリ
from datetime import datetime, timedelta
# パスワードを安全に保存するためのハッシュ化機能
from werkzeug.security import generate_password_hash
# 入力されたパスワードとハッシュ化済みパスワードを照合する機能
from werkzeug.security import check_password_hash
# SQLiteデータベースを操作するためのライブラリ
import sqlite3
# Flask本体と各種機能をインポート
from flask import Flask, redirect, render_template, request, session
# 使用するデータベースファイル名
DATABASE = "shift.db"
# Flaskアプリを作成
app = Flask(__name__)
# セッション機能に使用する秘密鍵
app.secret_key = "shift_app_secret"
csrf = CSRFProtect(app)


def init_db():
    """
    アプリ起動時に必要なテーブルを作成する関数
    初回起動時は管理者アカウントも自動作成する
    """
    # データベースへ接続
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # シフト情報を保存するテーブル
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
     # ユーザー情報を保存するテーブル
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
     # 確定済みシフトを保存するテーブル
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
     # 初回起動時に管理者ユーザーを作成
    cursor.execute(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        ("admin",)
    )
    # adminユーザーが存在するか確認
    admin_user = cursor.fetchone()
     # adminユーザーが存在しない場合のみ作成
    if admin_user is None:
        # パスワードをハッシュ化
        admin_password = generate_password_hash("admin123")
        # 管理者アカウントを登録
        cursor.execute(
            """
            INSERT INTO users (
                username,
                password,
                role
            )
            VALUES (?, ?, ?)
            """,
            ("admin", admin_password, "admin")
        )
     # 変更内容を保存
    conn.commit()
     # DB接続を終了    
    conn.close()


def get_db_connection():
    """
    データベース接続を返す共通関数
    """
    return sqlite3.connect(DATABASE)


init_db()





def is_admin():
    """
    ログイン中のユーザーが管理者かどうかを判定する関数
    """
     # データベースへ接続
    conn = get_db_connection()
     # セッションに保存されているユーザーIDからroleを取得
    cursor = conn.cursor()

    cursor.execute(
        "SELECT role FROM users WHERE id = ?",
        (session["user_id"],),
    )

    user = cursor.fetchone()
     # DB接続を終了
    conn.close()
     # roleがadminならTrue、それ以外ならFalseを返す
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
     # 既にログインしている場合はトップページへ移動
    if "user_id" in session:
        return redirect("/")
    # ユーザー登録フォームが送信された場合
    if request.method == "POST":
        # フォームに入力されたユーザー名とパスワードを取得
        username = request.form["username"]
        password = request.form["password"]

        # パスワードをハッシュ化して保存
        # 平文(そのままの文字列)では保存しない
        hashed_password = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hashed_password, "user"),
)

            # 登録したユーザーのIDをセッションへ保存
            # 自動的にログイン状態になる
            session["user_id"] = cursor.lastrowid

            conn.commit()
            conn.close()

            return redirect("/")
        # username の UNIQUE 制約に違反した場合
        # 同じユーザー名が既に存在する場合
        except sqlite3.IntegrityError:
            # DB接続を閉じる
            conn.close()
            # エラーメッセージを表示して登録画面を再表示
            return render_template(
                "register.html",
                error="そのユーザー名は既に使用されています",
            )
    # 初回アクセス時は登録画面を表示
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # 既にログインしている場合はトップページへ移動
    if "user_id" in session:
        return redirect("/")
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

    conn = get_db_connection()
    cursor = conn.cursor()
    # 確定対象のシフト情報を取得
    # usersテーブルと結合してユーザー名も取得する
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
    # 同じシフトが既に確定済みか確認
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
    # 既に確定済みの場合は一覧画面へ移動
    if result[0] > 0:
        conn.close()
        return redirect("/confirmed_shifts")
    # confirmed_shiftsテーブルへ確定シフトを登録
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


if __name__ == "__main__":
    app.run(debug=True, port=5001)
