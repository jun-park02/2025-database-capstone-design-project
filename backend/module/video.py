from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import Flask, request, send_file
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
from .database import cursor, db, execute
from datetime import datetime
from module.async_video import process_video_task
import pymysql
import os
import json

# 네임스페이스명 = Namespace('Swagger에 들어갈 제목', description='Swagger에 들어갈 설명')
video_ns = Namespace("Videos", path="/videos", description="비디오 관련 APIs")

upload_parser = reqparse.RequestParser()
upload_parser.add_argument("video", type=FileStorage, location="files", required=True)
upload_parser.add_argument("region", type=str, location="form", required=True)  # 지역
upload_parser.add_argument("date", type=str, location="form", required=True)    # YYYY-MM-DD
upload_parser.add_argument("time", type=str, location="form", required=True)    # HH:MM[:SS]

@video_ns.route("")
class VideoList(Resource):
    @video_ns.doc(
            description="비디오 목록 조회 또는 업로드",
            security=[{"BearerAuth": []}],
            responses={
                200: "비디오 목록 조회 성공",
                201: "비디오 업로드 성공",
                401: "Unauthorized"
            }
    )
    @jwt_required()
    def get(self):
        """비디오 목록 조회"""
        user_id = str(get_jwt_identity())

        sql = """
        SELECT video_id, file_path, task_id, region, recorded_at, status, created_at
        FROM videos
        WHERE user_id = %s AND status != 'DELETED'
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (user_id,))
        rows = cursor.fetchall()
        db.commit()

        videos = []
        for r in rows:
            if isinstance(r, dict):
                videos.append({
                    "video_id": r["video_id"],
                    "file_path": r["file_path"],
                    "task_id": r["task_id"],
                    "region": r["region"],
                    "recorded_at": r["recorded_at"].isoformat() if r["recorded_at"] else None,
                    "status": r["status"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                })
            else:
                videos.append({
                    "video_id": r[0],
                    "file_path": r[1],
                    "task_id": r[2],
                    "region": r[3],
                    "recorded_at": r[4].isoformat() if r[4] else None,
                    "status": r[5],
                    "created_at": r[6].isoformat() if r[6] else None,
                })

        return videos, 200

    @video_ns.doc(
            description="특정 지역의 도로 CCTV 영상 업로드",
            security=[{"BearerAuth": []}],
            responses={
                201: "업로드 성공",
                400: "Bad Request",
                401: "Unauthorized"
            }
    )
    @video_ns.expect(upload_parser)
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
        description="비디오 상세 조회",
        security=[{"BearerAuth": []}],
        responses={
            200: "조회 성공",
            404: "존재하지 않는 영상 혹은 권한 없음",
            401: "Unauthorized"
        }
    )
    @jwt_required()
    def get(self, video_id):
        """비디오 상세 조회"""
        user_id = str(get_jwt_identity())

        cursor.execute("""
            SELECT video_id, file_path, task_id, region, recorded_at, status, created_at
            FROM videos
            WHERE video_id = %s AND user_id = %s
        """, (video_id, user_id))
        row = cursor.fetchone()
        db.commit()

        if not row:
            return {"msg": "비디오를 찾을 수 없거나 권한이 없습니다."}, 404

        if isinstance(row, dict):
            return {
                "video_id": row["video_id"],
                "file_path": row["file_path"],
                "task_id": row["task_id"],
                "region": row["region"],
                "recorded_at": row["recorded_at"].isoformat() if row["recorded_at"] else None,
                "status": row["status"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            }, 200
        else:
            return {
                "video_id": row[0],
                "file_path": row[1],
                "task_id": row[2],
                "region": row[3],
                "recorded_at": row[4].isoformat() if row[4] else None,
                "status": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
            }, 200

    @video_ns.doc(
        description="비디오 삭제",
        security=[{"BearerAuth": []}],
        responses={
            204: "삭제 성공",
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

@video_ns.route("/<int:video_id>/download")
class VideoDownload(Resource):
    @video_ns.doc(
        description="처리된 비디오 파일 다운로드",
        security=[{"BearerAuth": []}],
        responses={
            200: "다운로드 성공",
            404: "비디오를 찾을 수 없거나 권한 없음 또는 처리된 파일이 없음",
            401: "Unauthorized",
            500: "서버 오류"
        }
    )
    @jwt_required()
    def get(self, video_id):
        user_id = str(get_jwt_identity())

        try:
            # 비디오 정보 조회 및 권한 확인
            cursor.execute("""
                SELECT user_id, file_path, status
                FROM videos
                WHERE video_id = %s AND user_id = %s
            """, (video_id, user_id))
            video_row = cursor.fetchone()
            db.commit()

            if not video_row:
                return {"msg": "비디오를 찾을 수 없거나 권한이 없습니다."}, 404

            # 비디오가 처리 완료되지 않은 경우
            if video_row.get("status") != "COMPLETED":
                return {"msg": "비디오 처리가 완료되지 않았습니다."}, 404

            # 원본 파일 경로에서 파일명 추출
            original_file_path = video_row.get("file_path")
            original_filename = os.path.basename(original_file_path)
            base_name = os.path.splitext(original_filename)[0]
            
            # 처리된 비디오 파일 경로 생성
            processed_dir = os.path.join("processed_video", user_id)
            processed_filename = f"{base_name}_counted.mp4"
            processed_file_path = os.path.join(processed_dir, processed_filename)

            # 파일 존재 확인
            if not os.path.exists(processed_file_path):
                return {"msg": "처리된 비디오 파일을 찾을 수 없습니다."}, 404

            # 파일 다운로드
            return send_file(
                processed_file_path,
                as_attachment=True,
                download_name=processed_filename,
                mimetype='video/mp4'
            )

        except Exception as e:
            db.rollback()
            return {"msg": "비디오 다운로드 중 오류가 발생했습니다.", "error": str(e)}, 500
    