from flask import Flask
import datetime

app = Flask(__name__)

# 나중에 변경, config로 분리
JWT_SECRET_KEY = "my_secret_key"
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

@app.route("/")
def hello_world():
    return "hello world"

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method

if __name__ == "__main__":
    app.run(debug=True)