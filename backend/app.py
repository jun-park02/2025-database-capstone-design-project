from flask_restx import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from module.login import auth_ns, auth_refresh_ns
from module.video import video_ns
from module.async_video import async_ns
from module.test import test_ns
from initApp import create_app
from dotenv import load_dotenv
import os, datetime
from module.init_db import init_db


load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

init_db()

app = create_app()

CORS(
    app,
    resources={r"/*": {"origins": "http://localhost:5173"}},
    supports_credentials=True,  # 쿠키/세션 쓰면 필요
)

app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES

authorizations = {
    "BearerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "JWT 인증용 헤더"
    }
}

api = Api(
    app,
    version="0.0.1",
    title="데이터베이스 캡스톤디자인 RestAPI",
    description="데이터베이스 캡스톤디자인 RestAPI",
    authorizations=authorizations
)

jwt = JWTManager(app)

api.add_namespace(auth_ns)
api.add_namespace(auth_refresh_ns)
api.add_namespace(test_ns)
api.add_namespace(video_ns)
api.add_namespace(async_ns)

if __name__ == "__main__":
    app.run(debug=True)