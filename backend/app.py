from flask_restx import Api
from flask_jwt_extended import JWTManager
from module.login import auth_ns, auth_refresh_ns
from module.test import test_ns
from initApp import create_app
from dotenv import load_dotenv
import os, datetime

load_dotenv()

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=3)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=7)

app = create_app()

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

if __name__ == "__main__":
    app.run(debug=True)