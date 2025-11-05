from flask import request, jsonify, make_response
from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from .database import cursor

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
auth_ns = Namespace("Auth", path="/auth", description="JWT 토큰을 리턴해주는 API")
auth_refresh_ns = Namespace("Refresh", path="/refresh", description="리프레시 토큰을 사용하여 JWT 토큰을 재발급 하는 API")

auth_ns_parser = reqparse.RequestParser()
auth_ns_parser.add_argument("username", type=int, location="form", required=True)
auth_ns_parser.add_argument("password", location="form", required=True)

@auth_ns.route("")
class Auth(Resource):
    @auth_ns.expect(auth_ns_parser)
    def post(self):
        # 2번째 매개변수는 default 값
        args = auth_ns_parser.parse_args()
        # default 값??
        username = args.get("username")
        password = args.get("password")

        sql = "SELECT user_id, password FROM users WHERE user_id = %s"
        cursor.execute(sql, (username))
        row = cursor.fetchone()

        # 아이디가 존재하지 않으면
        if row == None:
            print("test1")
            return {
                "msg": "Bad username or password"
            }, 401

        print(type(row['user_id']))
        print(type(row['password']))
        print(type(username))

        # 아이디와 비밀번호가 일치하면
        if username == row['user_id'] and password == row['password']:
            print("test2")
            refresh_token = create_refresh_token(identity=username)
            access_token = create_access_token(identity=username)

            return make_response(jsonify(access_token=access_token, refresh_token=refresh_token), 200)
        # 아이디와 비밀번호가 일치하지않으면
        else:
            print("test3")
            return {
                "msg": "Bad username or password"
            }, 401


auth_refresh_ns_parser = reqparse.RequestParser()
auth_refresh_ns_parser.add_argument("username", location="form", required=True)
auth_refresh_ns_parser.add_argument("password", location="form", required=True)

# refresh 토큰만 허용하기 위해, "refresh=True"를 사용
@auth_refresh_ns.route("")
class Refresh(Resource):
    @jwt_required(refresh=True)
    def post(self):
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        return jsonify(access_token=access_token)