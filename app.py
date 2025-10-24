from flask import Flask, jsonify
from flask import request
import datetime

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager

# 나중에 시크릿키 변경, 분리
# JWT_SECRET_KEY = "my_secret_key"
# JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
# JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)


app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "super-secret"  # Change this!
jwt = JWTManager(app)

@app.route("/")
def hello_world():
    return "hello world"

# Create a route to authenticate your users and return JWTs. The
# create_access_token() function is used to actually generate the JWT.
@app.route("/login", methods=["POST"])
def login():
    # 2번째 매개변수는 default 값
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    if username != "test" or password != "test":
        return jsonify({"msg": "Bad username or password"}), 401
    
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

# Protect a route with jwt_required, which will kick out requests
# without a valid JWT present.
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

if __name__ == "__main__":
    app.run(debug=True)