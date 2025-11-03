from flask import Flask, jsonify, request
from flask_restx import Api, Resource
import datetime



from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt

from login import auth_ns, auth_refresh_ns

# 나중에 시크릿키 변경, 분리
JWT_SECRET_KEY = "my_secret_key"
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES
api = Api(app)
jwt = JWTManager(app)

api.add_namespace(auth_ns)
api.add_namespace(auth_refresh_ns)

@app.route("/")
def hello_world():
    return "hello world"

# # Protect a route with jwt_required, which will kick out requests
# # without a valid JWT present.
# @app.route("/protected", methods=["GET"])
# @jwt_required()
# def protected():
#     # Access the identity of the current user with get_jwt_identity
#     current_user = get_jwt_identity()
#     claims = get_jwt()
#     return jsonify(identity=current_user, claims=claims), 200

if __name__ == "__main__":
    app.run(debug=True)