import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv
import os

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT"))
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")
DB_CHARSET = os.getenv("DB_CHARSET")

def get_conn():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset=DB_CHARSET,
        autocommit=False,  # 트랜잭션 제어를 위해 False 권장
        cursorclass=DictCursor,  # 결과를 dict로 받기
    )

def fetch_one(sql: str, params=None):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        row = cur.fetchone()
        conn.commit()
        return row
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()

def fetch_all(sql: str, params=None):
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        rows = cur.fetchall()
        conn.commit()
        return rows
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()

def execute(sql: str, params=None) -> int:
    """INSERT/UPDATE/DELETE"""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        affected = cur.execute(sql, params)
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()

def execute_lastrowid(sql: str, params=None) -> int:
    """INSERT/UPDATE/DELETE"""
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        lastrowid = cur.lastrowid
        conn.commit()
        return lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()

def executemany(sql: str, seq_params) -> int:
    conn = get_conn()
    cur = None
    try:
        cur = conn.cursor()
        affected = cur.executemany(sql, seq_params)
        conn.commit()
        return affected
    except Exception:
        conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        conn.close()




# Todo.예외처리
# 데이터베이스 연결
db = pymysql.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME,
    cursorclass=DictCursor,
    charset=DB_CHARSET
)

cursor = db.cursor()