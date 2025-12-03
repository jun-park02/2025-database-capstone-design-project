from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from .database import cursor, db, get_conn
from module.async_video import celery
import json

task_ns = Namespace("Tasks", path="/tasks", description="작업(Task) 관련 APIs")

@task_ns.route("")
class TaskList(Resource):
    @task_ns.doc(
        description="로그인한 유저의 작업 목록 조회",
        security=[{"BearerAuth": []}],
        responses={
            200: "작업 목록 조회 성공",
            401: "Unauthorized"
        }
    )
    @jwt_required()
    def get(self):
        """작업 목록 조회"""
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

@task_ns.route("/<string:task_id>")
class TaskStatus(Resource):
    @task_ns.doc(
        description="task_id로 작업 상태/결과 조회 (완료면 vehicle_counts DB 결과 반환)",
        security=[{"BearerAuth": []}],
        responses={200: "OK", 401: "Unauthorized"},
    )
    @jwt_required()
    def get(self, task_id: str):
        user_id = str(get_jwt_identity())

        # 1) Celery 상태(진행중/실패 등 기본 정보)
        result = celery.AsyncResult(task_id)
        payload = {"task_id": task_id, "state": result.state}

        if result.state == "PROGRESS" and isinstance(result.info, dict):
            payload["meta"] = result.info
            return payload, 200

        if result.state == "FAILURE":
            payload["error"] = str(result.info)
            payload["traceback"] = result.traceback
            return payload, 200

        # 2) SUCCESS(또는 DB상 COMPLETED)일 때: vehicle_counts에서 가져오기
        if result.state == "SUCCESS":
            db_conn = get_conn()
            try:
                with db_conn.cursor() as db_cursor:
                    # task_id -> video_id 찾기
                    sql = """
                    SELECT
                        v.video_id, v.user_id, v.region, v.recorded_at, v.file_path, v.status, v.created_at
                    FROM videos v
                    WHERE v.task_id = %s AND v.user_id = %s
                    LIMIT 1
                    """
                    db_cursor.execute(sql, (task_id, user_id))
                    video_row = db_cursor.fetchone()

                    # vehicle_counts에서 모든 차량 타입별 레코드 조회
                    vehicle_counts_rows = []
                    if video_row:
                        sql = """
                        SELECT
                            vc.vehicle_count_id,
                            vc.vehicle_type,
                            vc.forward_count,
                            vc.backward_count,
                            vc.created_at AS counted_at
                        FROM vehicle_counts vc
                        WHERE vc.video_id = %s
                        ORDER BY vc.vehicle_type
                        """
                        db_cursor.execute(sql, (video_row["video_id"],))
                        vehicle_counts_rows = db_cursor.fetchall()

                db_conn.commit()
            except Exception:
                db_conn.rollback()
                raise
            finally:
                db_conn.close()

            # 해당 task_id가 내 것이 아니거나 아직 videos에 없는 경우
            if not video_row:
                # 그래도 celery는 SUCCESS니까 최소한 celery result를 내려줌
                payload["result"] = result.result
                payload["warning"] = "DB에서 task_id에 해당하는 video/videos 레코드를 찾지 못했습니다."
                return payload, 200

            # vehicle_counts가 아직 안 들어온 경우(레이스 컨디션)
            if not vehicle_counts_rows:
                payload["video"] = {
                    "video_id": video_row["video_id"],
                    "region": video_row.get("region"),
                    "recorded_at": (video_row.get("recorded_at").isoformat(sep=" ") if video_row.get("recorded_at") else None),
                    "file_path": video_row.get("file_path"),
                    "status": video_row.get("status"),
                }
                payload["warning"] = "작업은 SUCCESS인데 vehicle_counts 저장이 아직 완료되지 않았습니다."
                # 필요하면 celery 결과도 같이 제공
                payload["result"] = result.result
                return payload, 200

            # 차량 타입별로 그룹화
            per_type_counts = []
            total_forward = 0
            total_backward = 0
            counted_at = None

            for vc_row in vehicle_counts_rows:
                vehicle_type = vc_row.get("vehicle_type")
                forward_count = vc_row.get("forward_count", 0)
                backward_count = vc_row.get("backward_count", 0)
                
                per_type_counts.append({
                    "vehicle_type": vehicle_type,
                    "forward_count": forward_count,
                    "backward_count": backward_count,
                })
                
                total_forward += forward_count
                total_backward += backward_count
                
                if counted_at is None:
                    counted_at = vc_row.get("counted_at")

            payload["video"] = {
                "video_id": video_row["video_id"],
                "region": video_row.get("region"),
                "recorded_at": (video_row.get("recorded_at").isoformat(sep=" ") if video_row.get("recorded_at") else None),
                "file_path": video_row.get("file_path"),
                "status": video_row.get("status"),
            }
            payload["vehicle_counts"] = {
                "total_forward": total_forward,
                "total_backward": total_backward,
                "per_type": per_type_counts,
                "counted_at": (counted_at.isoformat(sep=" ") if counted_at else None),
            }
            
            # celery result에서 추가 정보 포함 (선택사항)
            if result.result and isinstance(result.result, dict):
                payload["vehicle_counts"]["line_tol"] = result.result.get("line_tol")
                payload["vehicle_counts"]["frames_processed"] = result.result.get("frames_processed")
                payload["vehicle_counts"]["fps"] = result.result.get("fps")
                payload["vehicle_counts"]["output_path"] = result.result.get("output_path")
            
            return payload, 200

        # 나머지 상태(PENDING/STARTED/RETRY 등)
        return payload, 200

