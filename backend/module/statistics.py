from flask_restx import Resource, Namespace, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from .database import cursor, db
import json

statistics_ns = Namespace("Statistics", path="/statistics", description="통계 관련 APIs")

statistics_parser = reqparse.RequestParser()
statistics_parser.add_argument("region", type=str, location="args", required=False)
statistics_parser.add_argument("date", type=str, location="args", required=False)  # YYYY-MM-DD
statistics_parser.add_argument("time", type=str, location="args", required=False)  # HH:MM

@statistics_ns.route("/videos")
class VideoStatistics(Resource):
    @statistics_ns.doc(
        description="비디오 통행량 통계 조회",
        security=[{"BearerAuth": []}],
        responses={
            200: "통계 조회 성공",
            401: "Unauthorized"
        }
    )
    @statistics_ns.expect(statistics_parser)
    @jwt_required()
    def get(self):
        """비디오 통행량 통계 조회"""
        user_id = str(get_jwt_identity())
        args = statistics_parser.parse_args()
        region = args.get("region")
        date = args.get("date")
        time = args.get("time")

        # 기본 쿼리 구성 - videos만 먼저 조회
        sql = """
        SELECT 
            v.video_id,
            v.region,
            v.recorded_at
        FROM videos v
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
        video_rows = cursor.fetchall()
        db.commit()

        # 각 video_id에 대해 vehicle_counts 조회
        statistics = []
        for video_row in video_rows:
            video_id = video_row["video_id"] if isinstance(video_row, dict) else video_row[0]
            
            # 해당 video_id의 모든 차량 타입별 레코드 조회
            sql = """
            SELECT 
                vc.vehicle_type,
                vc.forward_count,
                vc.backward_count,
                vc.created_at AS counted_at
            FROM vehicle_counts vc
            WHERE vc.video_id = %s
            ORDER BY vc.vehicle_type
            """
            cursor.execute(sql, (video_id,))
            vehicle_counts_rows = cursor.fetchall()
            db.commit()

            # 차량 타입별로 그룹화
            per_type_counts = []
            total_forward = 0
            total_backward = 0
            counted_at = None

            for vc_row in vehicle_counts_rows:
                if isinstance(vc_row, dict):
                    vehicle_type = vc_row.get("vehicle_type")
                    forward_count = vc_row.get("forward_count", 0)
                    backward_count = vc_row.get("backward_count", 0)
                    if counted_at is None:
                        counted_at = vc_row.get("counted_at")
                else:
                    vehicle_type = vc_row[0]
                    forward_count = vc_row[1] if len(vc_row) > 1 else 0
                    backward_count = vc_row[2] if len(vc_row) > 2 else 0
                    if counted_at is None and len(vc_row) > 3:
                        counted_at = vc_row[3]

                per_type_counts.append({
                    "vehicle_type": vehicle_type,
                    "forward_count": forward_count,
                    "backward_count": backward_count,
                })
                
                total_forward += forward_count
                total_backward += backward_count

            # 응답 형식에 맞게 변환
            if isinstance(video_row, dict):
                statistics.append({
                    "video_id": video_row["video_id"],
                    "region": video_row["region"],
                    "recorded_at": video_row["recorded_at"].isoformat() if video_row["recorded_at"] else None,
                    "counted_at": counted_at.isoformat() if counted_at else None,
                    "vehicle_counts": {
                        "total_forward": total_forward,
                        "total_backward": total_backward,
                        "per_type": per_type_counts
                    }
                })
            else:
                # tuple인 경우
                statistics.append({
                    "video_id": video_row[0],
                    "region": video_row[1],
                    "recorded_at": video_row[2].isoformat() if video_row[2] else None,
                    "counted_at": counted_at.isoformat() if counted_at else None,
                    "vehicle_counts": {
                        "total_forward": total_forward,
                        "total_backward": total_backward,
                        "per_type": per_type_counts
                    }
                })

        return statistics, 200

