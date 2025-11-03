# app.py
from flask import Flask
from flask import request

app = Flask(__name__)
users = []  # 리스트에 회원 정보 저장

@app.route("/")
def index():
    return '<h3>메인 페이지</h3><a href="/register">회원가입</a> | <a href="/login">로그인</a>'

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]
        users.append({"name": name, "username": username, "password": password})
        return f"<p>{name}님 가입 완료!</p><a href='/login'>로그인하기</a>"
    return """
    <h2>회원가입</h2>
    <form method="post">
        이름: <input name="name"><br>
        아이디: <input name="username"><br>
        비밀번호: <input type="password" name="password"><br>
        <button>가입</button>
    </form>
    <p><a href="/login">로그인</a></p>
    """

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        for u in users:
            if u["username"] == username and u["password"] == password:
                return f"<h2>환영합니다, {u['name']}님!</h2>"
        return "로그인 실패! <a href='/login'>다시 시도</a>"
    return """
    <h2>로그인</h2>
    <form method="post">
        아이디: <input name="username"><br>
        비밀번호: <input type="password" name="password"><br>
        <button>로그인</button>
    </form>
    <p><a href="/register">회원가입</a></p>
    """

if __name__ == "__main__":
    app.run(debug=True)
