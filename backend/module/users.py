from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_bcrypt import Bcrypt
from .database import cursor, db
from pymysql.err import IntegrityError

users_ns = Namespace("Users", path="/users", description="사용자 관련 APIs")
bcrypt = Bcrypt()

register_parser = reqparse.RequestParser()
register_parser.add_argument("user_id", type=str, location="form", required=True)
register_parser.add_argument("password", type=str, location="form", required=True)
register_parser.add_argument("user_email", type=str, location="form", required=True)

reset_password_parser = reqparse.RequestParser()
reset_password_parser.add_argument("user_id", type=str, location="form", required=True)
reset_password_parser.add_argument("user_email", type=str, location="form", required=True)
reset_password_parser.add_argument("new_password", type=str, location="form", required=True)

@users_ns.route("")
class UserList(Resource):
    @users_ns.doc(
        description="회원가입",
        responses={
            201: "회원가입 성공",
            400: "이미 사용중인 아이디",
            500: "서버 오류"
        }
    )
    @users_ns.expect(register_parser)
    def post(self):
        """회원가입"""
        args = register_parser.parse_args()
        user_id = args.get("user_id")
        password = args.get("password")
        user_email = args.get("user_email")

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        try:
            sql = """
            INSERT INTO users (user_id, password_hash, user_email)
            VALUES (%s, %s, %s)
            """
            cursor.execute(sql, (user_id, password_hash, user_email))
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

@users_ns.route("/me")
class UserMe(Resource):
    @users_ns.doc(
        description="현재 사용자 정보 조회",
        security=[{"BearerAuth": []}],
        responses={
            200: "조회 성공",
            401: "Unauthorized"
        }
    )
    @jwt_required()
    def get(self):
        """현재 사용자 정보 조회"""
        user_id = str(get_jwt_identity())

        cursor.execute("""
            SELECT user_id, user_email, status, created_at
            FROM users
            WHERE user_id = %s
        """, (user_id,))
        row = cursor.fetchone()
        db.commit()

        if not row:
            return {"msg": "사용자를 찾을 수 없습니다."}, 404

        if isinstance(row, dict):
            return {
                "user_id": row["user_id"],
                "user_email": row["user_email"],
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }, 200
        else:
            return {
                "user_id": row[0],
                "user_email": row[1],
                "status": row[2],
                "created_at": row[3].isoformat() if row[3] else None,
            }, 200

    @users_ns.doc(
        description="회원탈퇴 (현재 사용자 계정을 INACTIVE 상태로 변경)",
        security=[{"BearerAuth": []}],
        responses={
            204: "회원탈퇴 완료",
            400: "이미 비활성화된 계정",
            401: "인증 실패",
            500: "서버 오류"
        }
    )
    @jwt_required()
    def delete(self):
        """회원탈퇴"""
        user_id = str(get_jwt_identity())

        try:
            cursor.execute(
                """
                UPDATE users
                SET status = 'INACTIVE'
                WHERE user_id = %s AND status != 'INACTIVE'
                """,
                (user_id,),
            )

            if cursor.rowcount == 0:
                db.rollback()
                return {"msg": "이미 비활성화된 계정이거나 존재하지 않는 사용자입니다."}, 400

            db.commit()
            return {"msg": "회원탈퇴가 완료되었습니다.", "user_id": user_id}, 200

        except Exception as e:
            db.rollback()
            return {"msg": "회원탈퇴 중 오류가 발생했습니다.", "error": str(e)}, 500

@users_ns.route("/password/reset")
class ResetPassword(Resource):
    @users_ns.doc(
        description="아이디와 이메일 검증 후 새 비밀번호로 재설정",
        responses={
            200: "비밀번호 재설정 성공",
            404: "일치하는 사용자 정보 없음",
            500: "서버 오류"
        }
    )
    @users_ns.expect(reset_password_parser)
    def put(self):
        """비밀번호 재설정"""
        args = reset_password_parser.parse_args()
        user_id = args.get("user_id")
        user_email = args.get("user_email")
        new_password = args.get("new_password")

        try:
            cursor.execute(
                "SELECT user_id FROM users WHERE user_id = %s AND user_email = %s",
                (user_id, user_email),
            )
            row = cursor.fetchone()

            if row is None:
                return {"msg": "해당 정보의 사용자를 찾을 수 없습니다."}, 404

            new_password_hash = bcrypt.generate_password_hash(new_password).decode("utf-8")
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE user_id = %s",
                (new_password_hash, user_id),
            )
            db.commit()

            return {"msg": "비밀번호가 성공적으로 재설정되었습니다."}, 200

        except Exception as e:
            db.rollback()
            return {"msg": "비밀번호 재설정 중 오류가 발생했습니다.", "error": str(e)}, 500

