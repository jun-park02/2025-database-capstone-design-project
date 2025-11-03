from flask import Flask, jsonify, request
from flask_restx import Api, Resource
import datetime
from flask_jwt_extended import create_access_token, create_refresh_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt
from module.login import auth_ns, auth_refresh_ns
from module.test import test_ns
from dotenv import load_dotenv
import os

# 
load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES
api = Api(app)
jwt = JWTManager(app)

api.add_namespace(auth_ns)
api.add_namespace(auth_refresh_ns)
api.add_namespace(test_ns)

if __name__ == "__main__":
    app.run(debug=True)