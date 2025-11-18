from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
video_ns = Namespace("Video", path="/video", description="비디오 관련 APIs")

# ----- ↓↓↓ 비디오 업로드 들어갈 곳 ↓↓↓ -----
upload_parser = reqparse.RequestParser()
# 여기에 add_argument (module/login.py 처럼). 아래는 예시
# upload_parset.add_argument("video", type=FileStorage, location="files", required=True)

@video_ns.route("/video")
class Video(Resource):
    # @jwt_required()는 로그인 되어 있을때만 접근 가능하다는 것을 나타냄
    @jwt_required()
    @video_ns.expect(upload_parser)
    def post(self):
        args = upload_parser.parse_args()
        # args.get으로 필요한 정보, 비디오 파일 받아오기

        # 아래 코드를 사용하면 identity에 user_id가 들어감
        # identity = get_jwt_identity()

        # backend/uploaded_video/user_id(동적으로)/example.mp4 이런 경로로 업로드하게 만들기
        # werkzeug.utils의 secure_filename() 함수 사용하기

        # ----------- 여기서 부터 구현 -----------

# ----- ↑↑↑ 비디오 업로드 들어갈 곳 ↑↑↑ -----