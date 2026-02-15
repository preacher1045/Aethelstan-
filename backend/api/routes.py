from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.config import MODEL_PATH
from backend.ingestion.pcap_loader import extract_features_from_upload
from backend.insight.generator import InsightGenerator
from backend.ml.production_inference import predict_with_feature_engineering
from backend.storage.repository import (
	create_anomaly_result,
	create_insight,
	create_pcap_session,
	create_traffic_window,
	list_anomaly_results,
	list_insights,
	list_pcap_sessions,
	update_pcap_session,
)


router = APIRouter()


def _normalize_results(results: Dict[str, Any]) -> Dict[str, Any]:
	scores = results.get("scores")
	predictions = results.get("predictions")
	return {
		"n_samples": results.get("n_samples"),
		"anomaly_count": results.get("anomaly_count"),
		"anomaly_ratio": results.get("anomaly_ratio"),
		"anomaly_percentage": results.get("anomaly_percentage"),
		"scores": scores.tolist() if hasattr(scores, "tolist") else list(scores or []),
		"predictions": predictions.tolist() if hasattr(predictions, "tolist") else list(predictions or []),
	}


def _build_traffic_window_data(
	session_id: str,
	window_id: int,
	record: Dict[str, Any],
) -> Dict[str, Any]:
	return {
		"session_id": session_id,
		"window_id": window_id,
		"window_start": record.get("window_start"),
		"window_end": record.get("window_end"),
		"packet_count": record.get("packet_count"),
		"total_bytes": record.get("total_bytes"),
		"avg_packet_size": record.get("avg_packet_size"),
		"min_packet_size": record.get("min_packet_size"),
		"max_packet_size": record.get("max_packet_size"),
		"packet_size_std": record.get("packet_size_std"),
		"tcp_count": record.get("tcp_count"),
		"udp_count": record.get("udp_count"),
		"icmp_count": record.get("icmp_count"),
		"other_count": record.get("other_count"),
		"tcp_ratio": record.get("tcp_ratio"),
		"udp_ratio": record.get("udp_ratio"),
		"icmp_ratio": record.get("icmp_ratio"),
		"other_ratio": record.get("other_ratio"),
		"unique_src_ips": record.get("unique_src_ips"),
		"unique_dst_ips": record.get("unique_dst_ips"),
		"unique_src_ratio": record.get("unique_src_ratio"),
		"unique_dst_ratio": record.get("unique_dst_ratio"),
		"flow_count": record.get("flow_count"),
		"flow_ratio": record.get("flow_ratio"),
		"avg_flow_packets": record.get("avg_flow_packets"),
		"avg_flow_bytes": record.get("avg_flow_bytes"),
		"packets_per_sec": record.get("packets_per_sec"),
		"bytes_per_sec": record.get("bytes_per_sec"),
		"port_diversity": record.get("port_diversity"),
		"avg_inter_arrival_time": record.get("avg_inter_arrival_time"),
		"connection_rate": record.get("connection_rate"),
		"features_json": record,
	}


def _build_anomaly_result_data(
	session_id: str,
	window_id: int,
	traffic_window_id: Optional[int],
	record: Dict[str, Any],
) -> Dict[str, Any]:
	return {
		"session_id": session_id,
		"window_id": window_id,
		"traffic_window_id": traffic_window_id,
		"is_anomaly": bool(record.get("is_anomaly")) if "is_anomaly" in record else record.get("anomaly") == -1,
		"anomaly_score": record.get("anomaly_score") if record.get("anomaly_score") is not None else record.get("score"),
		"confidence_score": record.get("confidence_score"),
		"prediction_label": record.get("prediction_label"),
		"model_name": record.get("model_name"),
		"model_version": record.get("model_version"),
		"threshold_used": record.get("threshold_used"),
		"baseline_deviation": record.get("baseline_deviation"),
		"severity_level": record.get("severity_level"),
		"contributing_features": record.get("contributing_features"),
		"anomaly_type": record.get("anomaly_type"),
		"tags": record.get("tags"),
		"processing_time_ms": record.get("processing_time_ms"),
	}


@router.post("/upload")
async def upload_pcap(file: UploadFile = File(...)) -> Dict[str, Any]:
	session_id = str(uuid4())
	create_pcap_session(
		{
			"session_id": session_id,
			"filename": file.filename,
			"status": "processing",
		}
	)

	try:
		saved_path, features_json = extract_features_from_upload(file, session_id)
		results = predict_with_feature_engineering(str(features_json), model_path=str(MODEL_PATH))
		records = results["detailed_results"].to_dict(orient="records")

		packet_total = sum(int(r.get("packet_count", 0) or 0) for r in records)
		window_starts = [r.get("window_start") for r in records if r.get("window_start") is not None]
		window_ends = [r.get("window_end") for r in records if r.get("window_end") is not None]
		start_ts = min(window_starts) if window_starts else None
		end_ts = max(window_ends) if window_ends else None
		duration = (end_ts - start_ts) if start_ts is not None and end_ts is not None else None

		update_pcap_session(
			session_id,
			{
				"filepath": str(saved_path),
				"file_size_bytes": saved_path.stat().st_size,
				"total_packets": packet_total,
				"start_timestamp": start_ts,
				"end_timestamp": end_ts,
				"duration_seconds": duration,
				"status": "completed",
			},
		)

		for idx, record in enumerate(records):
			window_id = idx + 1
			window_row = create_traffic_window(_build_traffic_window_data(session_id, window_id, record))
			create_anomaly_result(
				_build_anomaly_result_data(
					session_id,
					window_id,
					window_row.get("id"),
					record,
				)
			)

		insight_generator = InsightGenerator(max_alerts=5)
		insight_report = insight_generator.generate(records)
		create_insight(
			{
				"session_id": session_id,
				"insight_type": "summary",
				"summary": insight_report.get("summary", ""),
				"details": insight_report.get("stats"),
			}
		)
		for alert in insight_report.get("alerts", []):
			create_insight(
				{
					"session_id": session_id,
					"insight_type": "alert",
					"alert_type": alert.get("alert_type"),
					"severity": alert.get("severity"),
					"confidence": alert.get("confidence"),
					"summary": alert.get("summary", ""),
					"details": alert.get("details"),
					"tags": alert.get("details", {}).get("tags"),
					"packet_count": alert.get("details", {}).get("packet_count"),
					"total_bytes": alert.get("details", {}).get("total_bytes"),
					"unique_src_ips": alert.get("details", {}).get("unique_src_ips"),
					"unique_dst_ips": alert.get("details", {}).get("unique_dst_ips"),
					"packets_per_sec": alert.get("details", {}).get("packets_per_sec"),
					"bytes_per_sec": alert.get("details", {}).get("bytes_per_sec"),
				}
			)

		return {
			"session_id": session_id,
			"features_file": str(features_json),
			"results": _normalize_results(results),
			"insights": insight_report,
		}
	except Exception as exc:
		update_pcap_session(
			session_id,
			{
				"status": "failed",
				"error_message": str(exc),
			},
		)
		raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sessions")
def get_sessions(status: Optional[str] = None, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
	return list_pcap_sessions(status=status, limit=limit, offset=offset)


@router.get("/results/{session_id}")
def get_results(session_id: str, is_anomaly: Optional[bool] = None) -> List[Dict[str, Any]]:
	return list_anomaly_results(session_id=session_id, is_anomaly=is_anomaly, limit=10000, offset=0)


@router.get("/insights/{session_id}")
def get_insights(session_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
	return list_insights(session_id=session_id, status=status, limit=10000, offset=0)
