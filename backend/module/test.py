from flask import jsonify
from flask_restx import Resource, Namespace
from dotenv import load_dotenv
from flask_jwt_extended import jwt_required, get_jwt_identity

load_dotenv()

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
test_ns = Namespace("Test", path="/test", description="테스트 API")

@test_ns.route("/protected")
class Auth(Resource):
    @jwt_required()
    def post(self):
        current_user = get_jwt_identity()
        return jsonify(identity=current_user)