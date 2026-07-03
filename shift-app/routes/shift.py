from datetime import datetime, timedelta

from flask import Blueprint, redirect, render_template, request, session

from database import get_db_connection
from routes.auth import login_required

shift_bp = Blueprint("shift", __name__)

@shift_bp.route("/", methods=["GET", "POST"])
@login_required
def home():
    """
    トップページの処理
    GET：ログイン中ユーザーのシフト一覧を表示
    POST：入力されたシフトを登録
    """
    user_id = session.get("user_id")

    if request.method == "POST":
        name = request.form.get("name")
        date = request.form.get("date")
        time = request.form.get("time")
        end_time = request.form.get("end_time")

        with get_db_connection() as conn:
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

        return redirect("/")

    today = datetime.today().date()
    two_weeks_later = today + timedelta(days=14)

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, date, time, end_time
            FROM shifts
            WHERE user_id = ?
              AND date >= ?
              AND date <= ?
            ORDER BY date
            """,
            (user_id, str(today), str(two_weeks_later)),
        )
        rows = cursor.fetchall()

    shifts = [
        {
            "id": row[0],
            "name": row[1],
            "date": row[2],
            "time": row[3],
            "end_time": row[4],
        }
        for row in rows
    ]

    return render_template(
        "index.html",
        shifts=shifts,
        username=session.get("username"),
        is_admin_user=session.get("role") == "admin",
    )
    
@shift_bp.route("/edit/<int:id>")
@login_required
def edit(id):
    user_id = session.get("user_id")
    """
    シフト編集画面を表示する
    """
    

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, name, date, time, end_time
            FROM shifts
            WHERE id = ?
              AND user_id = ?
            """,
            (id, user_id),
        )
        row = cursor.fetchone()

    if row is None:
        return redirect("/")

    shift = {
        "id": row[0],
        "name": row[1],
        "date": row[2],
        "time": row[3],
        "end_time": row[4],
    }

    return render_template("edit.html", shift=shift)

@shift_bp.route("/update/<int:id>", methods=["POST"])
@login_required
def update(id):
    """
    シフト情報を更新する
    """
    user_id = session.get("user_id")



    name = request.form.get("name")
    date = request.form.get("date")
    time = request.form.get("time")
    end_time = request.form.get("end_time")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE shifts
            SET name = ?, date = ?, time = ?, end_time = ?
            WHERE id = ?
              AND user_id = ?
            """,
            (name, date, time, end_time, id, user_id),
        )
        conn.commit()

    return redirect("/")

@shift_bp.route("/delete/<int:id>", methods=["POST"])
@login_required
def delete(id):
    """
    シフト情報を削除する
    """
    user_id = session.get("user_id")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            DELETE FROM shifts
            WHERE id = ?
              AND user_id = ?
            """,
            (id, user_id),
        )
        conn.commit()

    return redirect("/")
