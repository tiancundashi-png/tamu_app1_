import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "shift.db")


def get_db_connection():
    """
    データベース接続を返す共通関数
    """
    return sqlite3.connect(DATABASE)