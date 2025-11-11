import mysql.connector
from mysql.connector import errorcode, IntegrityError
from flask import Flask, request

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="dbs48167475"
)
cursor = db.cursor()

cursor.execute("CREATE DATABASE IF NOT EXISTS dblogin DEFAULT CHARACTER SET utf8mb4")
cursor.execute("USE dblogin")

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
""")

app = Flask(__name__)

@app.route("/")
def index():
    return '<h3>메인 페이지</h3><a href="/register">회원가입</a> | <a href="/login">로그인</a>'

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        try:
            cursor.execute(
                "INSERT INTO users (name, username, password) VALUES (%s, %s, %s)",
                (name, username, password)
            )
            db.commit()
            return f"{name}님 가입 완료! <a href='/login'>로그인하기</a>"
        except IntegrityError as e:
            
            if e.errno == errorcode.ER_DUP_ENTRY:
                return "이미 사용 중인 아이디입니다. <a href='/register'>다시 시도</a>"
            raise
    return """
    <h2>회원가입</h2>
    <form method="post">
        이름: <input name="name"><br>
        아이디: <input name="username"><br>
        비밀번호: <input type="password" name="password"><br>
        <button>가입</button>
    </form>
    """

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        cursor.execute(
            "SELECT id, name FROM users WHERE username=%s AND password=%s",
            (username, password)
        )
        user = cursor.fetchone()
        if user:
            return f"{username}님 로그인 성공!"
        return "로그인 실패! <a href='/login'>다시 시도</a>"
    return """
    <h2>로그인</h2>
    <form method="post">
        아이디: <input name="username"><br>
        비밀번호: <input type="password" name="password"><br>
        <button>로그인</button>
    </form>
    """

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
