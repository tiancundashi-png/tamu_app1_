from functools import wraps
import sqlite3

from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from database import get_db_connection
auth_bp = Blueprint("auth", __name__)

def is_admin():
    """
    ログイン中のユーザーが管理者かどうかを判定する
    """
    return session.get("role") == "admin"


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")

        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")

        if not is_admin():
            return redirect("/")

        return func(*args, **kwargs)

    return wrapper





@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/")

    if session.get("login_failed_count", 0) >= 5:
        return render_template(
            "login.html",
            error="ログイン失敗が多すぎます。しばらくしてから再度お試しください。"
        )

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, username, password, role
                FROM users
                WHERE username = ?
                """,
                (username,),
            )
            user = cursor.fetchone()

        if user is not None and check_password_hash(user[2], password):
            session["user_id"] = user[0]
            session["username"] = user[1]
            session["role"] = user[3]
            session.pop("login_failed_count", None)
            return redirect("/")

        session["login_failed_count"] = session.get("login_failed_count", 0) + 1

        return render_template(
            "login.html",
            error="ユーザー名またはパスワードが違います"
        )

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """
    ログアウト処理
    """
    # セッション情報を削除してログアウト
    session.clear()

    return redirect("/login")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    管理者が新規ユーザーを登録する
    """
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "admin":
        return redirect("/")

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        hashed_password = generate_password_hash(password)

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                    (username, hashed_password, "user"),
                )
                conn.commit()

            return redirect("/admin")

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="そのユーザー名は既に使用されています",
            )

    return render_template("register.html")