from flask import Blueprint, redirect, render_template, request

from database import get_db_connection
from routes.auth import admin_required

admin_bp = Blueprint("admin", __name__)

@admin_bp.route("/admin")
@admin_required
def admin():
    """
    管理者画面を表示する
    未確定のシフト希望を一覧表示する
    """
    selected_date = request.args.get("date")

    with get_db_connection() as conn:
        cursor = conn.cursor()

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
                (selected_date,),
            )
        else:
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

        rows = cursor.fetchall()

    shifts = [
        {
            "id": row[0],
            "username": row[1],
            "date": row[2],
            "time": row[3],
            "end_time": row[4],
        }
        for row in rows
    ]

    return render_template(
        "admin.html",
        shifts=shifts,
        selected_date=selected_date,
    )
    
@admin_bp.route("/confirm_shift/<int:shift_id>")
@admin_required
def confirm_shift(shift_id):
    """
    管理者がシフト確定画面を表示する
    """
    with get_db_connection() as conn:
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
            (shift_id,),
        )
        row = cursor.fetchone()

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

@admin_bp.route("/confirm_shift/<int:shift_id>", methods=["POST"])
@admin_required
def confirm_shift_post(shift_id):
    """
    管理者がシフトを確定する
    """
    date = request.form.get("date")
    time = request.form.get("time")
    end_time = request.form.get("end_time")

    with get_db_connection() as conn:
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
            (shift_id,),
        )
        shift = cursor.fetchone()

        if shift is None:
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
            (shift[0], date, time, end_time),
        )
        result = cursor.fetchone()

        if result[0] > 0:
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
            (shift[0], shift[1], date, time, end_time),
        )

        cursor.execute(
            """
            DELETE FROM shifts
            WHERE id = ?
            """,
            (shift_id,),
        )

        conn.commit()

    return redirect("/admin")

@admin_bp.route("/confirmed_shifts")
@admin_required
def confirmed_shifts():
    """
    確定済みシフト一覧を表示する
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, user_id, username, date, time, end_time
            FROM confirmed_shifts
            ORDER BY date
            """
        )

        rows = cursor.fetchall()

    shifts = [
        {
            "id": row[0],
            "user_id": row[1],
            "username": row[2],
            "date": row[3],
            "time": row[4],
            "end_time": row[5],
        }
        for row in rows
    ]

    return render_template(
        "confirmed_shifts.html",
        shifts=shifts,
    )

@admin_bp.route("/users")
@admin_required
def users():
    with get_db_connection() as conn:
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

    return render_template("users.html", users=users)

@admin_bp.route("/delete_user_confirm/<int:user_id>")
@admin_required
def delete_user_confirm(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )

        user = cursor.fetchone()

    if user is None:
        return redirect("/users")

    if user[2] == "admin":
        return redirect("/users")

    user_data = {
        "id": user[0],
        "username": user[1],
        "role": user[2],
    }

    return render_template(
        "delete_user_confirm.html",
        user=user_data,
    )
    
@admin_bp.route("/delete_user/<int:user_id>", methods=["POST"])
@admin_required
def delete_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT role
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )

        user = cursor.fetchone()

        if user is None:
            return redirect("/users")

        if user[0] == "admin":
            return redirect("/users")

        cursor.execute(
            """
            DELETE FROM shifts
            WHERE user_id = ?
            """,
            (user_id,),
        )

        cursor.execute(
            """
            DELETE FROM confirmed_shifts
            WHERE user_id = ?
            """,
            (user_id,),
        )

        cursor.execute(
            """
            DELETE FROM users
            WHERE id = ?
            """,
            (user_id,),
        )

        conn.commit()

    return redirect("/users")