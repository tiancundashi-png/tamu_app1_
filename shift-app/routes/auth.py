from flask import Blueprint, redirect, render_template, request, session
from werkzeug.security import check_password_hash

from database import get_db_connection

auth_bp = Blueprint("auth", __name__)





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