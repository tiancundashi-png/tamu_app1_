import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "shift.db"

new_password = "ここに新しいパスワード"

conn = sqlite3.connect(DATABASE)
cursor = conn.cursor()

cursor.execute(
    """
    UPDATE users
    SET password = ?
    WHERE username = ?
    """,
    (
        generate_password_hash(new_password),
        "admin"
    )
)

conn.commit()
conn.close()

print("管理者パスワードを変更しました")