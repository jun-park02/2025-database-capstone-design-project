# app.py
from flask import Flask,jsonify
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
        return jsonify({"msg":name})


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
       
    if users["test"] == username and users["test"] == password:
        return f"{users[username]}성공"
    return "로그인 실패! <a href='/login'>다시 시도</a>"


if __name__ == "__main__":
    app.run(debug=True)
