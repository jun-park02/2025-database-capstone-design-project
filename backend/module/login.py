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
auth_ns = Namespace("Auth", path="/auth", description="로그인관련 APIs")
auth_refresh_ns = Namespace("Refresh", path="/refresh", description="리프레시 토큰을 사용하여 JWT 토큰을 재발급 하는 API")

# ----- 회원가입 들어갈 곳 -----
register_parser = reqparse.RequestParser()
register_parser.add_argument("user_id", type=str, location="form", required=True)
register_parser.add_argument("password", type=str, location="form", required=True)

@auth_ns.route("/register")
class Register(Resource):
    @auth_ns.expect(register_parser)
    def post(self):
        args = register_parser.parse_args()
        user_id = args.get("user_id")
        password = args.get("password")

        # 해시화 하는걸로 수정하기
        # DB에다가 해시된걸 저장 -> 코드에서 미리 해시하고 db에 저장
        # 아마도 hashed = bcrypt.hashpw(password, bcrypt.gensalt()) 이거
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            sql = """
            INSERT INTO users (user_id, password_hash)
            VALUES (%s, %s)
            """
            cursor.execute(sql, (user_id, password_hash))
            db.commit()

            return {
                "msg": "회원가입 성공",
                "user_id": user_id,
            }, 201

        except IntegrityError as e:
            # user_id UNIQUE 제약 조건 위반
            if e.args[0] == 1062:
                return {
                    "msg": "이미 사용 중인 아이디입니다."
                }, 400
            
            db.rollback()
            return {"msg": "회원가입 중 오류 발생", "error": str(e)}, 500
# ----------------------------
    
login_parser = reqparse.RequestParser()
login_parser.add_argument("user_id", type=str, location="form", required=True)
login_parser.add_argument("password", type=str, location="form", required=True)

@auth_ns.route("/login")
class Auth(Resource):
    @auth_ns.expect(login_parser)
    def post(self):
        args = login_parser.parse_args()
        user_id = args.get("user_id")
        password = args.get("password")

        sql = "SELECT user_id, password_hash FROM users WHERE user_id = %s"
        cursor.execute(sql, (user_id, ))
        row = cursor.fetchone()

        # 아이디가 존재하지 않으면
        if row == None:
            print("test1")
            return {
                "msg": "Bad user_id or password"
            }, 401

        # 비밀번호가 일치하면
        if bcrypt.check_password_hash(row["password_hash"], password):
            print("test2")
            refresh_token = create_refresh_token(identity=user_id)
            access_token = create_access_token(identity=user_id)

            return make_response(jsonify(access_token=access_token, refresh_token=refresh_token), 200)
        # 아이디와 비밀번호가 일치하지 않으면
        else:
            print("test3")
            return {
                "msg": "Bad user_id or password"
            }, 401


# refresh 토큰만 허용하기 위해, "refresh=True"를 사용
@auth_ns.route("/refresh")
class Auth(Resource):
    @auth_ns.doc(
            description="Refresh 토큰으로 새 Access 토큰 발급",
            security=[{"BearerAuth": []}],
            responses={
                200: "새 access_token 발급 성공",
                401: "유효하지 않은 또는 만료된 refresh 토큰"
            }
    )
    @jwt_required(refresh=True)
    def post(self):
        identity = get_jwt_identity()
        access_token = create_access_token(identity=identity)
        return jsonify(access_token=access_token)