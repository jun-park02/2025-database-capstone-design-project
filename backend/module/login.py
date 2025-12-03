from flask import jsonify, make_response
from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
# Todo. 불러오지 말고 아래에 import db 한거 사용해서 하는걸로 수정하기
# from .database import cursor, db <- 이거 사용
# login 처럼 cursor 사용해서 하기
from pymysql.err import IntegrityError
from .database import cursor, db

bcrypt = Bcrypt()

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
auth_ns = Namespace("Auth", path="/auth", description="인증 관련 APIs")

# ---------------------------------------- 로그인 ----------------------------------------
    
login_parser = reqparse.RequestParser()
login_parser.add_argument("user_id", type=str, location="form", required=True)
login_parser.add_argument("password", type=str, location="form", required=True)

@auth_ns.route("/login")
class Auth(Resource):
    @auth_ns.doc(
            description="id와 password를 입력받아 Access 토큰 발급",
            security=[{"BearerAuth": []}],
            responses={
                200: "access_token 발급 성공",
                401: "잘못된 id 또는 password"
            }
    )
    @auth_ns.expect(login_parser)
    def post(self):
        args = login_parser.parse_args()
        user_id = args.get("user_id")
        password = args.get("password")

        sql = "SELECT user_id, password_hash, status FROM users WHERE user_id = %s"
        cursor.execute(sql, (user_id, ))
        row = cursor.fetchone()

        # 아이디가 존재하지 않으면
        if row == None:
            return {
                "msg": "Bad user_id or password"
            }, 401

        # 비활성화된 계정인 경우 로그인 거부
        if row.get("status") == "INACTIVE":
            return {
                "msg": "비활성화된 계정입니다."
            }, 401

        # 비밀번호가 일치하면
        if bcrypt.check_password_hash(row["password_hash"], password):
            refresh_token = create_refresh_token(identity=user_id)
            access_token = create_access_token(identity=user_id)

            return make_response(jsonify(access_token=access_token, refresh_token=refresh_token), 200)
        # 아이디와 비밀번호가 일치하지 않으면
        else:
            return {
                "msg": "Bad user_id or password"
            }, 401