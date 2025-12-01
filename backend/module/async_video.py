# module/async_job.py
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from celery import Celery
from .database import cursor, db
from ultralytics import YOLO
import os, time
import json
import pymysql
import cv2

async_ns = Namespace("Async", path="/async", description="Celery/Redis 영상 비동기 작업 APIs")

def make_celery():
    # .env 에서 가져오도록 구성 (없으면 로컬 기본값)
    broker_url = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
    backend_url = os.getenv("CELERY_RESULT_BACKEND") or broker_url

    c = Celery("capstone_async", broker=broker_url, backend=backend_url)
    c.conf.update(
        task_track_started=True,
        result_extended=True,
        accept_content=["json"],
        task_serializer="json",
        result_serializer="json",
        timezone="Asia/Seoul",
        enable_utc=False,
    )
    return c

# Celery 앱 인스턴스(워커가 import 해서 사용)
celery = make_celery()

# ---------------- YOLO / Tracking / Counting ----------------
# COCO class ids: 2 car, 3 motorcycle, 5 bus, 7 truck
VEHICLE_CLASS_IDS = [2, 3, 5, 7]

# 전역 모델 캐시(워커 프로세스 안에서 재사용)
_MODEL = None

def get_model():
    global _MODEL
    if _MODEL is None:
        model_path = os.getenv("YOLO_MODEL_PATH", "yolov8n.pt")
        _MODEL = YOLO(model_path)
    return _MODEL

# ---------- 기하 유틸 ----------
def _side(p, a, b):
    # 점 p가 직선 AB 의 어느 쪽(부호)인지
    (x, y), (x1, y1), (x2, y2) = p, a, b
    return (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)

def _crossed(prev_p, curr_p, a, b, tol=3):
    # prev->curr 이동 중 AB를 가로질렀는가 (부호가 바뀌면 교차)
    s1 = _side(prev_p, a, b)
    s2 = _side(curr_p, a, b)
    if abs(s1) < tol:
        s1 = 0
    if abs(s2) < tol:
        s2 = 0
    return s1 * s2 < 0

def _direction(prev_p, curr_p, a, b):
    # 교차가 일어났다면, 이동이 AB의 어느 쪽을 향했는지(법선 기준) 판정
    (x1, y1), (x2, y2) = a, b
    dx, dy = (x2 - x1), (y2 - y1)
    nx, ny = dy, -dx  # AB의 법선(한쪽 방향)
    vx, vy = (curr_p[0] - prev_p[0], curr_p[1] - prev_p[1])  # 이동벡터
    dot = vx * nx + vy * ny
    return "FORWARD" if dot > 0 else "BACKWARD"

def _parse_point(s: str):
    # "300,320" -> (300, 320)
    x_str, y_str = s.split(",")
    return (int(float(x_str.strip())), int(float(y_str.strip())))

def count_vehicles_in_video(task, user_id: str, input_path: str):
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Video not found: {input_path}")

    # cap = cv2.VideoCapture(input_path)
    # if not cap.isOpened():
    #     raise RuntimeError(f"Cannot open video: {input_path}")

    # fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    # w0 = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    # h0 = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    # total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {input_path}")

    # fps는 유지 (0이면 fallback)
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 30.0

    # ✅ width/height는 cap.get() 대신 첫 프레임으로 확정
    ok, first = cap.read()
    if not ok or first is None:
        raise RuntimeError("Cannot read first frame to infer size")

    h0, w0 = first.shape[:2]

    # 다시 처음부터 처리
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    # frame_count는 여전히 0일 수 있으니 fallback 허용
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)

    # ---------- 리사이즈 옵션 ----------
    resize_w = int(os.getenv("RESIZE_W", "0"))  # 0이면 원본
    if resize_w and w0 > 0 and h0 > 0:
        target_w = resize_w
        target_h = int(h0 * (resize_w / w0))
    else:
        target_w, target_h = w0, h0

    # ---------- 카운트 기준선(임의 선분 A->B) ----------
    # Env로 지정 가능: COUNT_LINE_A="300,320" COUNT_LINE_B="900,200"
    if os.getenv("COUNT_LINE_A") and os.getenv("COUNT_LINE_B"):
        line_a = _parse_point(os.getenv("COUNT_LINE_A"))
        line_b = _parse_point(os.getenv("COUNT_LINE_B"))
    else:
        # 기본값(대충 화면에서 보이는 사선). 영상에 맞춰 env로 꼭 조정하는 걸 추천.
        line_a = (int(target_w * 0.30), int(target_h * 0.60))
        line_b = (int(target_w * 0.90), int(target_h * 0.40))

    line_tol = int(os.getenv("LINE_TOL", "6"))

    # ---------- 필터/트래커 ----------
    tracker_yaml = os.getenv("YOLO_TRACKER", "bytetrack.yaml")
    conf_thr = float(os.getenv("YOLO_CONF", "0.35"))
    iou = float(os.getenv("YOLO_IOU", "0.45"))

    # class name 필터: 기본은 COCO 기준 차량류
    # (ultralytics COCO 기본 라벨은 보통 'motorcycle' 입니다. 'motorbike'도 같이 허용)
    vehicle_class_names = set(
        x.strip() for x in os.getenv(
            "VEHICLE_CLASS_NAMES", "car,bus,truck,motorcycle,motorbike"
        ).split(",") if x.strip()
    )

    # ---------- 결과 영상 저장(옵션) ----------
    save_annotated = os.getenv("SAVE_ANNOTATED_VIDEO", "1") == "1"
    out_path = None
    writer = None
    if save_annotated and target_w > 0 and target_h > 0:
        base = os.path.splitext(os.path.basename(input_path))[0]
        out_dir = os.path.join("processed_video", str(user_id))
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{base}_counted.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, fps, (target_w, target_h))

    model = get_model()
    names = getattr(model, "names", {})  # cls_id -> cls_name

    # ---------- 상태 ----------
    last_pos = {}              # track_id -> (cx, cy)
    counted_forward = set()    # track_id
    counted_backward = set()   # track_id
    total_forward = 0
    total_backward = 0
    per_class_forward = {}     # cls_name -> count
    per_class_backward = {}    # cls_name -> count

    frame_idx = 0
    progress_every = int(os.getenv("PROGRESS_EVERY_N_FRAMES", "10"))

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        frame_idx += 1

        if resize_w and target_w > 0 and target_h > 0:
            frame = cv2.resize(frame, (target_w, target_h))

        # 한 프레임 트래킹 (persist=True로 ID 유지)
        results = model.track(
            frame,
            persist=True,
            tracker=tracker_yaml,
            conf=conf_thr,
            iou=iou,
            verbose=False,
        )

        r = results[0]
        boxes = getattr(r, "boxes", None)

        # 시각화 프레임(필요 시)
        vis = frame
        if writer is not None:
            vis = frame.copy()
            cv2.line(vis, line_a, line_b, (0, 255, 255), 2)
            cv2.circle(vis, line_a, 5, (0, 255, 255), -1)
            cv2.circle(vis, line_b, 5, (0, 255, 255), -1)
            cv2.putText(vis, "A", (line_a[0] + 6, line_a[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(vis, "B", (line_b[0] + 6, line_b[1] - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        if boxes is not None and len(boxes) > 0 and boxes.id is not None:
            xyxy = boxes.xyxy.cpu().numpy()
            clses = boxes.cls.cpu().numpy().astype(int)
            ids = boxes.id.cpu().numpy().astype(int)
            confs = boxes.conf.cpu().numpy()

            for (x1, y1, x2, y2), cls_id, tid, cf in zip(xyxy, clses, ids, confs):
                if cf < conf_thr:
                    continue

                cls_name = names.get(int(cls_id), str(int(cls_id)))
                if cls_name not in vehicle_class_names:
                    continue

                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                curr_p = (cx, cy)
                prev_p = last_pos.get(int(tid), curr_p)

                # 선분 교차 + 방향 판정
                if _crossed(prev_p, curr_p, line_a, line_b, tol=line_tol):
                    dir_ = _direction(prev_p, curr_p, line_a, line_b)
                    if dir_ == "FORWARD":
                        if int(tid) not in counted_forward:
                            counted_forward.add(int(tid))
                            total_forward += 1
                            per_class_forward[cls_name] = per_class_forward.get(cls_name, 0) + 1
                    else:
                        if int(tid) not in counted_backward:
                            counted_backward.add(int(tid))
                            total_backward += 1
                            per_class_backward[cls_name] = per_class_backward.get(cls_name, 0) + 1

                last_pos[int(tid)] = curr_p

                # 박스/ID 시각화(옵션)
                if writer is not None:
                    cv2.rectangle(vis, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                    cv2.circle(vis, (cx, cy), 3, (0, 0, 255), -1)
                    cv2.putText(vis, f"{cls_name} ID{int(tid)}",
                                (int(x1), max(0, int(y1) - 6)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (50, 50, 255), 1)

        # 카운트 패널 + 저장
        if writer is not None:
            cv2.rectangle(vis, (10, 10), (360, 90), (0, 0, 0), -1)
            cv2.putText(vis, f"FORWARD (A->B): {total_forward}", (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.putText(vis, f"BACKWARD (B->A): {total_backward}", (20, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            writer.write(vis)

        # 진행률 업데이트
        if progress_every > 0 and frame_idx % progress_every == 0:
            meta = {
                "current_frame": frame_idx,
                "total_forward": total_forward,
                "total_backward": total_backward,
            }
            if total_frames > 0:
                meta["total_frames"] = total_frames
                meta["progress"] = round(frame_idx / total_frames, 4)
            task.update_state(state="PROGRESS", meta=meta)

    cap.release()
    if writer is not None:
        writer.release()

    return {
        "msg": "비동기 처리 완료(임의 선분 교차 기반 차량 카운트)",
        "input_path": input_path,
        "output_path": out_path,
        "total_forward": total_forward,
        "total_backward": total_backward,
        "per_class_forward": per_class_forward,
        "per_class_backward": per_class_backward,
        "line_a": line_a,
        "line_b": line_b,
        "line_tol": line_tol,
        "fps": fps,
        "frames_processed": frame_idx,
        "resize": {"enabled": bool(resize_w), "target_w": target_w, "target_h": target_h},
        "vehicle_class_names": sorted(list(vehicle_class_names)),
    }

@celery.task(bind=True)
def process_video_task(self, user_id: str, file_path: str, video_id: int):
    input_path = os.path.abspath(file_path)
    task_id = self.request.id

    try:
        result = count_vehicles_in_video(self, user_id, input_path)

        cursor.execute("""
            INSERT INTO vehicle_counts (
                video_id, user_id,
                total_forward, total_backward,
                per_class_forward, per_class_backward,
                line_a_x, line_a_y, line_b_x, line_b_y
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            video_id, user_id,
            int(result.get("total_forward", 0)),
            int(result.get("total_backward", 0)),
            json.dumps(result.get("per_class_forward", {}), ensure_ascii=False),
            json.dumps(result.get("per_class_backward", {}), ensure_ascii=False),
            int(result["line_a"][0]), int(result["line_a"][1]),
            int(result["line_b"][0]), int(result["line_b"][1]),
        ))

        sql = """
            UPDATE videos SET status='COMPLETED' WHERE task_id=%s
        """

        cursor.execute(sql, (task_id,))
        db.commit()

        return result
    except Exception:
        sql = """
            UPDATE videos SET status='FAIL' WHERE task_id=%s
        """

        cursor.execute(sql, (task_id,))
        db.commit()
        raise


# ----- API: 작업 등록 -----
enqueue_parser = reqparse.RequestParser()
enqueue_parser.add_argument("file_path", type=str, location="json", required=True, help="업로드된 비디오 경로")

@async_ns.route("/process-video")
class ProcessVideo(Resource):
    @async_ns.doc(
        description="비디오 후처리(비동기) 작업을 큐에 등록",
        security=[{"BearerAuth": []}],
        responses={202: "Accepted", 401: "Unauthorized"},
    )
    @async_ns.expect(enqueue_parser)
    @jwt_required()
    def post(self):
        args = enqueue_parser.parse_args()
        user_id = str(get_jwt_identity())
        file_path = args["file_path"]

        task = process_video_task.delay(user_id, file_path)

        return {
            "msg": "작업이 큐에 등록되었습니다",
            "task_id": task.id,
        }, 202


# ----- API: 작업 상태/결과 조회 -----
# @async_ns.route("/tasks/<string:task_id>")
# class TaskStatus(Resource):
#     @async_ns.doc(
#         description="task_id로 작업 상태/결과 조회",
#         security=[{"BearerAuth": []}],
#         responses={200: "OK", 401: "Unauthorized"},
#     )
#     @jwt_required()
#     def get(self, task_id: str):
#         result = celery.AsyncResult(task_id)
#         payload = {"task_id": task_id, "state": result.state}

#         if result.state == "PROGRESS" and isinstance(result.info, dict):
#             payload["meta"] = result.info
#         elif result.state == "SUCCESS":
#             payload["result"] = result.result
#         elif result.state == "FAILURE":
#             payload["error"] = str(result.info)
#             payload["traceback"] = result.traceback

#         return payload, 200

def get_db_connection():
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT"))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

@async_ns.route("/tasks/<string:task_id>")
class TaskStatus(Resource):
    @async_ns.doc(
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
            db = get_db_connection()
            try:
                with db.cursor() as cursor:
                    # task_id -> video_id 찾고, vehicle_counts 조인
                    sql = """
                    SELECT
                        v.video_id, v.user_id, v.region, v.recorded_at, v.file_path, v.status, v.created_at,
                        vc.vehicle_count_id,
                        vc.total_forward, vc.total_backward,
                        vc.per_class_forward, vc.per_class_backward,
                        vc.line_a_x, vc.line_a_y, vc.line_b_x, vc.line_b_y,
                        vc.created_at AS counted_at
                    FROM videos v
                    LEFT JOIN vehicle_counts vc ON vc.video_id = v.video_id
                    WHERE v.task_id = %s AND v.user_id = %s
                    ORDER BY vc.created_at DESC
                    LIMIT 1
                    """
                    cursor.execute(sql, (task_id, user_id))
                    row = cursor.fetchone()

                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

            # 해당 task_id가 내 것이 아니거나 아직 videos에 없는 경우
            if not row:
                # 그래도 celery는 SUCCESS니까 최소한 celery result를 내려줌
                payload["result"] = result.result
                payload["warning"] = "DB에서 task_id에 해당하는 video/videos 레코드를 찾지 못했습니다."
                return payload, 200

            # vehicle_counts가 아직 안 들어온 경우(레이스 컨디션)
            if row.get("vehicle_count_id") is None:
                payload["video"] = {
                    "video_id": row["video_id"],
                    "region": row.get("region"),
                    "recorded_at": (row.get("recorded_at").isoformat(sep=" ") if row.get("recorded_at") else None),
                    "file_path": row.get("file_path"),
                    "status": row.get("status"),
                }
                payload["warning"] = "작업은 SUCCESS인데 vehicle_counts 저장이 아직 완료되지 않았습니다."
                # 필요하면 celery 결과도 같이 제공
                payload["result"] = result.result
                return payload, 200

            # JSON 컬럼(또는 TEXT로 저장된 JSON) dict로 복원
            def _loads(v):
                if v is None:
                    return {}
                if isinstance(v, (dict, list)):
                    return v
                try:
                    return json.loads(v)
                except Exception:
                    return {"_raw": v}

            payload["video"] = {
                "video_id": row["video_id"],
                "region": row.get("region"),
                "recorded_at": (row.get("recorded_at").isoformat(sep=" ") if row.get("recorded_at") else None),
                "file_path": row.get("file_path"),
                "status": row.get("status"),
            }
            payload["vehicle_counts"] = {
                "vehicle_count_id": row["vehicle_count_id"],
                "total_forward": row.get("total_forward", 0),
                "total_backward": row.get("total_backward", 0),
                "per_class_forward": _loads(row.get("per_class_forward")),
                "per_class_backward": _loads(row.get("per_class_backward")),
                "line_a": [row.get("line_a_x"), row.get("line_a_y")],
                "line_b": [row.get("line_b_x"), row.get("line_b_y")],
                "line_tol": row.get("line_tol"),
                "frames_processed": row.get("frames_processed"),
                "fps": row.get("fps"),
                "output_path": row.get("output_path"),
                "counted_at": (row.get("counted_at").isoformat(sep=" ") if row.get("counted_at") else None),
            }
            return payload, 200

        # 나머지 상태(PENDING/STARTED/RETRY 등)
        return payload, 200