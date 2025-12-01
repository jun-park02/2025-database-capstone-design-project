from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Flask, request
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from .database import cursor, db
from datetime import datetime
from module.async_video import process_video_task
import pymysql
import os

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
video_ns = Namespace("Video", path="/video", description="비디오 관련 APIs")

upload_parser = reqparse.RequestParser()
upload_parser.add_argument("video", type=FileStorage, location="files", required=True)
upload_parser.add_argument("region", type=str, location="form", required=True)  # 지역
upload_parser.add_argument("date", type=str, location="form", required=True)    # YYYY-MM-DD
upload_parser.add_argument("time", type=str, location="form", required=True)    # HH:MM[:SS]

@video_ns.route("/video")
class Video(Resource):
    @video_ns.doc(
            description="",
            security=[{"BearerAuth": []}],
            responses={
                200: "",
                401: ""
            }
    )

    # @jwt_required()는 로그인 되어 있을때만 접근 가능하다는 것을 나타냄
    @video_ns.expect(upload_parser)
    @jwt_required()
    def post(self):
        print(1)
        args = upload_parser.parse_args()
        print(args)
        # args.get으로 필요한 정보, 비디오 파일 받아오기

        # 아래 코드를 사용하면 identity에 user_id가 들어감
        # identity = get_jwt_identity()

        # backend/uploaded_video/user_id(동적으로)/example.mp4 이런 경로로 업로드하게 만들기
        # werkzeug.utils의 secure_filename() 함수 사용하기

        # ----------- 여기서 부터 구현 -----------
        print("content_type:", request.content_type)
        print("request.files:", request.files)

        video_file: FileStorage = args.get("video")
        region: str = (args.get("region") or "").strip()
        date_s: str = (args.get("date") or "").strip()
        time_s: str = (args.get("time") or "").strip()

        print(region)
        print(date_s)
        print(time_s)

        if not region:
            return {"msg": "region 값이 필요합니다."}, 400

        # date/time 검증 및 recorded_at 생성
        try:
            # time이 HH:MM 이면 :00 붙임
            if len(time_s.split(":")) == 2:
                time_s = time_s + ":00"
            recorded_at = datetime.strptime(f"{date_s} {time_s}", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return {"msg": "date는 YYYY-MM-DD, time은 HH:MM 또는 HH:MM:SS 형식이어야 합니다."}, 400

        user_id = str(get_jwt_identity())
        filename = secure_filename(video_file.filename)

        user_dir = os.path.join("uploaded_video", user_id)
        os.makedirs(user_dir, exist_ok=True)

        save_path = os.path.join(user_dir, filename)
        video_file.save(save_path)

        print("cwd:", os.getcwd())
        print("save_path:", save_path)
        print("abs_path:", os.path.abspath(save_path))
        print("exists:", os.path.exists(save_path))
        print("size:", os.path.getsize(save_path) if os.path.exists(save_path) else None)

        cursor.execute("""
            INSERT INTO videos (user_id, file_path, task_id, region, recorded_at, status)
            VALUES (%s, %s, %s, %s, %s, 'PROCESSING')
        """, (user_id, save_path, "PENDING", region, recorded_at))
        video_id = cursor.lastrowid
        db.commit()

        task = process_video_task.delay(user_id, save_path, video_id)

        cursor.execute("UPDATE videos SET task_id=%s WHERE video_id=%s", (task.id, video_id))
        
        db.commit()

        return {
            "msg": "비디오 업로드 성공",
            "file": save_path,
            "task_id": task.id
        }, 201
    
# ================================================================================================

@video_ns.route("/tasks")
class VideoTasks(Resource):
    @video_ns.doc(
        description="로그인한 유저의 videos.task_id 전체 조회",
        security=[{"BearerAuth": []}],
        responses={
            200: "OK",
            401: "Unauthorized"
        }
    )
    @jwt_required()
    def get(self):
        user_id = str(get_jwt_identity())

        sql = """
        SELECT task_id, status
        FROM videos
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
        db.commit()

        # cursor 설정에 따라 tuple/dict 다를 수 있어서 둘 다 안전하게 처리
        tasks = []
        for r in rows:
            if isinstance(r, dict):
                tasks.append({
                    "task_id": r["task_id"],
                    "status": r["status"],
                })
            else:
                tasks.append({
                    "task_id": r[0],
                    "status": r[1],
                })

        return {
            "user_id": user_id,
            "count": len(tasks),
            "tasks": tasks
        }, 200
    