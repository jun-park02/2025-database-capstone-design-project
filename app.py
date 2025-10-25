from flask import Flask, jsonify
from flask import request
import datetime

from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt

# 나중에 시크릿키 변경, 분리
JWT_SECRET_KEY = "my_secret_key"
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES
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
    
    refresh_token = create_refresh_token(identity=username)
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token, refresh_token=refresh_token)

# We are using the `refresh=True` options in jwt_required to only allow
# refresh tokens to access this route.
@app.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(access_token=access_token)

# Protect a route with jwt_required, which will kick out requests
# without a valid JWT present.
@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    current_user = get_jwt_identity()
    claims = get_jwt()
    return jsonify(identity=current_user, claims=claims), 200

if __name__ == "__main__":
    app.run(debug=True)