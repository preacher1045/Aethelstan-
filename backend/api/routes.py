from __future__ import annotations
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile

from backend.config import MODEL_PATH
from backend.ingestion.pcap_loader import extract_features_from_path, save_upload_file
from backend.insight.generator import InsightGenerator
from backend.ml.production_inference import predict_with_feature_engineering
from backend.storage.repository import (
	create_anomaly_result,
	create_flow,
	create_insight,
	create_pcap_session,
	create_port_stat,
	create_traffic_window,
	list_anomaly_results,
	list_flows,
	list_insights,
	list_port_stats,
	list_pcap_sessions,
	list_traffic_windows,
	update_pcap_session,
)
import json

router = APIRouter()


def _validate_upload(file: UploadFile) -> None:
	if not file.filename:
		raise HTTPException(status_code=400, detail="Filename is required.")
	suffix = Path(file.filename).suffix.lower()
	if suffix not in {".pcap", ".pcapng"}:
		raise HTTPException(status_code=400, detail="Only .pcap or .pcapng files are supported.")


def _process_session(session_id: str, saved_path: Path) -> None:
	try:
		saved_path, features_json = extract_features_from_path(saved_path, session_id)
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

			for flow in record.get("top_flows") or []:
				create_flow(
					{
						"session_id": session_id,
						"window_id": window_id,
						"src_ip": flow.get("src_ip"),
						"dst_ip": flow.get("dst_ip"),
						"src_port": flow.get("src_port"),
						"dst_port": flow.get("dst_port"),
						"protocol": flow.get("protocol"),
						"packet_count": flow.get("packet_count"),
						"total_bytes": flow.get("total_bytes"),
						"duration_seconds": flow.get("duration_seconds"),
						"start_timestamp": flow.get("start_timestamp"),
						"end_timestamp": flow.get("end_timestamp"),
					}
				)

			for port_stat in record.get("port_stats") or []:
				create_port_stat(
					{
						"session_id": session_id,
						"window_id": window_id,
						"port": port_stat.get("port"),
						"protocol": port_stat.get("protocol"),
						"service_name": port_stat.get("service_name"),
						"packet_count": port_stat.get("packet_count"),
						"total_bytes": port_stat.get("total_bytes"),
					}
				)

		insight_generator = InsightGenerator(max_alerts=5)
		insight_report = insight_generator.generate(records)

		create_insight(
			{
				"session_id": session_id,
				"insight_type": "summary",
				"summary": insight_report.get("summary", ""),
				"details": json.dumps(insight_report.get("stats")) if insight_report.get("stats") else None,
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
					"details": json.dumps(alert.get("details")) if alert.get("details") else None,
					"tags": json.dumps(alert.get("details", {}).get("tags")) if alert.get("details", {}).get("tags") else None,
					"packet_count": alert.get("details", {}).get("packet_count"),
					"total_bytes": alert.get("details", {}).get("total_bytes"),
					"unique_src_ips": alert.get("details", {}).get("unique_src_ips"),
					"unique_dst_ips": alert.get("details", {}).get("unique_dst_ips"),
					"packets_per_sec": alert.get("details", {}).get("packets_per_sec"),
					"bytes_per_sec": alert.get("details", {}).get("bytes_per_sec"),
				}
			)
	except Exception as exc:
		update_pcap_session(
			session_id,
			{
				"status": "failed",
				"error_message": str(exc),
			},
		)


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
        # Phase 2: TCP Health Metrics
        "tcp_syn_count": record.get("tcp_syn_count"),
        "tcp_ack_count": record.get("tcp_ack_count"),
        "tcp_rst_count": record.get("tcp_rst_count"),
        "tcp_fin_count": record.get("tcp_fin_count"),
        "tcp_retransmissions": record.get("tcp_retransmissions"),
        # Phase 2: Distribution Histograms (already JSON from Rust)
        "packet_size_distribution": json.dumps(record.get("packet_size_distribution")) if record.get("packet_size_distribution") else None,
        "flow_duration_distribution": json.dumps(record.get("flow_duration_distribution")) if record.get("flow_duration_distribution") else None,
        "features_json": json.dumps(record),  # ← serialize dict to JSON string
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
        "contributing_features": json.dumps(record.get("contributing_features")) if record.get("contributing_features") else None,  # ← serialize
        "anomaly_type": record.get("anomaly_type"),
        "tags": json.dumps(record.get("tags")) if record.get("tags") else None,  # ← serialize
        "processing_time_ms": record.get("processing_time_ms"),
    }

@router.post("/upload")
async def upload_pcap(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> Dict[str, Any]:
	_validate_upload(file)
	session_id = str(uuid4())
	create_pcap_session(
		{
			"session_id": session_id,
			"filename": file.filename,
			"status": "processing",
		}
	)

	try:
		saved_path = save_upload_file(file, session_id)
		background_tasks.add_task(_process_session, session_id, saved_path)
		return {
			"session_id": session_id,
			"status": "processing",
			"filename": file.filename,
		}
	except Exception as exc:
		update_pcap_session(
			session_id,
			{
				"status": "failed",
				"error_message": str(exc),
				"completed_at": datetime.now(datetime.timezone.utc),
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


@router.get("/traffic-windows/{session_id}")
def get_traffic_windows(session_id: str) -> List[Dict[str, Any]]:
	return list_traffic_windows(session_id=session_id, limit=10000, offset=0)


@router.get("/flows/{session_id}")
def get_flows(session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
	return list_flows(session_id=session_id, limit=limit, offset=offset)


@router.get("/port-stats/{session_id}")
def get_port_stats(session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
	return list_port_stats(session_id=session_id, limit=limit, offset=offset)
