from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Flask, request
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from .database import cursor, db, execute
from datetime import datetime
from module.async_video import process_video_task
import pymysql
import os
import json

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
            description="특정 지역의 도로 CCTV 영상 업로드",
            security=[{"BearerAuth": []}],
            responses={
                200: "업로드 성공",
                401: "Unauthorized"
            }
    )
    @video_ns.expect(upload_parser)
    # JWT토큰이 있어야만 실행
    @jwt_required()
    def post(self):
        args = upload_parser.parse_args()

        video_file: FileStorage = args.get("video")
        region: str = (args.get("region") or "").strip()
        date_s: str = (args.get("date") or "").strip()
        time_s: str = (args.get("time") or "").strip()

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

@video_ns.route("/<int:video_id>")
class VideoDetail(Resource):
    @video_ns.doc(
        description="비디오 삭제",
        security=[{"BearerAuth": []}],
        responses={
            200: "삭제 성공",
            404: "존재하지 않는 영상 혹은 권한 없음",
            500: "서버 오류"
        }
    )
    @jwt_required()
    def delete(self, video_id):
        user_id = str(get_jwt_identity())

        try:
            cursor.execute(
                "UPDATE videos SET status = 'DELETED' WHERE video_id = %s AND user_id = %s",
                (video_id, user_id),
            )

            if cursor.rowcount == 0:
                db.rollback()
                return {"msg": "삭제할 비디오를 찾을 수 없거나 권한이 없습니다."}, 404

            db.commit()

            return {"msg": "비디오 상태가 DELETED로 변경되었습니다.", "video_id": video_id}, 200

        except Exception as e:
            db.rollback()
            return {"msg": "비디오 삭제 중 오류가 발생했습니다.", "error": str(e)}, 500
    
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

# ================================================================================================

statistics_parser = reqparse.RequestParser()
statistics_parser.add_argument("region", type=str, location="args", required=False)
statistics_parser.add_argument("date", type=str, location="args", required=False)  # YYYY-MM-DD
statistics_parser.add_argument("time", type=str, location="args", required=False)  # HH:MM

@video_ns.route("/statistics")
class VideoStatistics(Resource):
    @video_ns.doc(
        description="통행량 통계 조회 API",
        security=[{"BearerAuth": []}],
        responses={
            200: "통계 조회 성공",
            401: "Unauthorized"
        }
    )
    @video_ns.expect(statistics_parser)
    @jwt_required()
    def get(self):
        user_id = str(get_jwt_identity())
        args = statistics_parser.parse_args()
        region = args.get("region")
        date = args.get("date")
        time = args.get("time")

        print(region)
        print(date)
        print(time)

        # 기본 쿼리 구성
        sql = """
        SELECT 
            v.video_id,
            v.region,
            v.recorded_at,
            vc.created_at AS counted_at,
            vc.total_forward,
            vc.total_backward,
            vc.per_class_forward,
            vc.per_class_backward
        FROM videos v
        INNER JOIN vehicle_counts vc ON v.video_id = vc.video_id
        WHERE v.user_id = %s
          AND v.status != 'DELETED'
        """
        params = [user_id]

        # 필터 조건 추가
        if region:
            sql += " AND v.region = %s"
            params.append(region)

        if date:
            sql += " AND DATE(v.recorded_at) = %s"
            params.append(date)

        if time:
            # HH:MM 형식으로 시간 비교 (분 단위까지)
            sql += " AND TIME_FORMAT(v.recorded_at, '%%H:%%i') = %s"
            params.append(time)

        sql += " ORDER BY v.recorded_at DESC"

        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        db.commit()

        # JSON 필드를 안전하게 파싱하는 헬퍼 함수
        def _loads_json(v):
            if v is None:
                return {}
            if isinstance(v, (dict, list)):
                return v
            try:
                return json.loads(v)
            except Exception:
                return {}

        # 응답 형식에 맞게 변환
        statistics = []
        for row in rows:
            if isinstance(row, dict):
                statistics.append({
                    "video_id": row["video_id"],
                    "region": row["region"],
                    "recorded_at": row["recorded_at"].isoformat() if row["recorded_at"] else None,
                    "counted_at": row["counted_at"].isoformat() if row["counted_at"] else None,
                    "vehicle_counts": {
                        "total_forward": row["total_forward"],
                        "total_backward": row["total_backward"],
                        "per_class_forward": _loads_json(row.get("per_class_forward")),
                        "per_class_backward": _loads_json(row.get("per_class_backward"))
                    }
                })
            else:
                # tuple인 경우 (DictCursor를 사용하므로 일반적으로 dict)
                statistics.append({
                    "video_id": row[0],
                    "region": row[1],
                    "recorded_at": row[2].isoformat() if row[2] else None,
                    "counted_at": row[3].isoformat() if row[3] else None,
                    "vehicle_counts": {
                        "total_forward": row[4],
                        "total_backward": row[5],
                        "per_class_forward": _loads_json(row[6] if len(row) > 6 else None),
                        "per_class_backward": _loads_json(row[7] if len(row) > 7 else None)
                    }
                })

        print(statistics)

        return statistics, 200
    