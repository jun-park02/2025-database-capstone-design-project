from flask_restx import Api
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from module.login import auth_ns
from module.video import video_ns
from module.tasks import task_ns
from module.statistics import statistics_ns
from module.users import users_ns
from module.init_db import init_db
from init_app import create_app
from dotenv import load_dotenv
import os, datetime

load_dotenv()
init_db()
app = create_app()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(days=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", 1)))

JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=int(os.getenv("JWT_REFRESH_TOKEN_EXPIRES", 7)))

app.config["JWT_SECRET_KEY"] = JWT_SECRET_KEY
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = JWT_ACCESS_TOKEN_EXPIRES

CORS(
    app,
    resources={r"/*": {"origins": "http://localhost:5173"}},
    supports_credentials=True,  # 쿠키/세션 쓰면 필요
)

authorizations = {
    "BearerAuth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "JWT 인증 헤더"
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
api.add_namespace(users_ns)
api.add_namespace(video_ns)
api.add_namespace(task_ns)
api.add_namespace(statistics_ns)

if __name__ == "__main__":
    app.run(debug=True)