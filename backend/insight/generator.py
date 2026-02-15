"""
Generate human-readable insights from model outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import math


@dataclass
class Insight:
    alert_type: str
    severity: str
    confidence: float
    summary: str
    details: Dict[str, Any]


class InsightGenerator:
    """Create concise, useful insights from anomaly detection outputs."""

    def __init__(self, max_alerts: int = 5) -> None:
        self.max_alerts = max_alerts

    def generate(self, records: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a digestible insight report from model output records.

        Expected record fields (best-effort):
        - score: float
        - is_anomaly: bool (optional)
        - anomaly: int (-1/1) (optional)
        - window_start, window_end (optional)
        - packet_count, bytes_per_sec, packets_per_sec (optional)
        - tcp_ratio, udp_ratio, icmp_ratio, other_ratio (optional)
        - unique_src_ips, unique_dst_ips, flow_count (optional)
        """
        records_list = list(records)
        if not records_list:
            return {
                "summary": "No records available for insight generation.",
                "alerts": [],
                "stats": {"total_windows": 0, "anomalies": 0},
            }

        scores = [self._safe_float(r.get("score")) for r in records_list]
        score_stats = self._score_stats(scores)
        anomalies = [self._is_anomaly(r, score_stats) for r in records_list]

        scored_records = [
            (self._safe_float(r.get("score")), idx, r, anomalies[idx])
            for idx, r in enumerate(records_list)
        ]

        scored_records.sort(key=lambda x: x[0])
        top_candidates = [item for item in scored_records if item[3]]
        if not top_candidates:
            top_candidates = scored_records

        top_candidates = top_candidates[: self.max_alerts]

        alerts = [self._build_insight(idx, r, score, score_stats) for score, idx, r, _ in top_candidates]

        summary = self._build_summary(records_list, anomalies, score_stats)

        return {
            "summary": summary,
            "alerts": [self._to_dict(a) for a in alerts],
            "stats": {
                "total_windows": len(records_list),
                "anomalies": sum(1 for a in anomalies if a),
                "score_min": score_stats["min"],
                "score_max": score_stats["max"],
                "score_mean": score_stats["mean"],
            },
        }

    def _build_insight(
        self,
        idx: int,
        record: Dict[str, Any],
        score: float,
        score_stats: Dict[str, float],
    ) -> Insight:
        confidence = self._score_to_confidence(score, score_stats)
        alert_type, tags = self._infer_alert_type(record)
        severity = self._severity_from_confidence(confidence)

        summary = self._compose_summary(idx, record, alert_type, severity, confidence)
        details = self._compose_details(record, tags)

        return Insight(
            alert_type=alert_type,
            severity=severity,
            confidence=confidence,
            summary=summary,
            details=details,
        )

    def _compose_summary(
        self,
        idx: int,
        record: Dict[str, Any],
        alert_type: str,
        severity: str,
        confidence: float,
    ) -> str:
        window_start = record.get("window_start")
        window_end = record.get("window_end")
        packet_count = record.get("packet_count")
        bytes_per_sec = record.get("bytes_per_sec")

        window_desc = f"Window {idx + 1}"
        if window_start is not None and window_end is not None:
            window_desc = f"Window {idx + 1} ({window_start:.2f}–{window_end:.2f})"

        parts = [
            f"{window_desc}: {alert_type} detected.",
            f"Severity: {severity}",
            f"Confidence: {confidence:.2%}",
        ]

        if packet_count is not None:
            parts.append(f"Packets: {int(packet_count):,}")
        if bytes_per_sec is not None:
            parts.append(f"Bytes/sec: {float(bytes_per_sec):,.0f}")

        return " | ".join(parts)

    def _compose_details(self, record: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
        detail_fields = [
            "packet_count",
            "total_bytes",
            "avg_packet_size",
            "packets_per_sec",
            "bytes_per_sec",
            "tcp_ratio",
            "udp_ratio",
            "icmp_ratio",
            "other_ratio",
            "unique_src_ips",
            "unique_dst_ips",
            "flow_count",
            "avg_flow_packets",
            "avg_flow_bytes",
        ]

        details = {k: record.get(k) for k in detail_fields if k in record}
        details["tags"] = tags
        return details

    def _infer_alert_type(self, record: Dict[str, Any]) -> Tuple[str, List[str]]:
        tcp = self._safe_float(record.get("tcp_ratio"))
        udp = self._safe_float(record.get("udp_ratio"))
        icmp = self._safe_float(record.get("icmp_ratio"))
        packets_per_sec = self._safe_float(record.get("packets_per_sec"))
        unique_src = self._safe_float(record.get("unique_src_ips"))

        tags = []

        if udp > 0.75:
            tags.append("udp_dominant")
        if tcp > 0.75:
            tags.append("tcp_dominant")
        if icmp > 0.2:
            tags.append("icmp_elevated")
        if packets_per_sec > 100000:
            tags.append("high_packet_rate")
        if unique_src > 5000:
            tags.append("many_sources")

        if "udp_dominant" in tags and "high_packet_rate" in tags:
            return "Potential UDP Flood", tags
        if "tcp_dominant" in tags and "high_packet_rate" in tags:
            return "Potential TCP Flood", tags
        if "icmp_elevated" in tags:
            return "ICMP Activity Spike", tags
        if "many_sources" in tags:
            return "Distributed Source Activity", tags

        return "Anomalous Traffic Pattern", tags

    def _score_to_confidence(self, score: float, stats: Dict[str, float]) -> float:
        if stats["min"] == stats["max"]:
            return 0.5
        # Lower scores are more anomalous
        normalized = (stats["max"] - score) / (stats["max"] - stats["min"])
        return max(0.0, min(1.0, normalized))

    def _severity_from_confidence(self, confidence: float) -> str:
        if confidence >= 0.85:
            return "Critical"
        if confidence >= 0.7:
            return "High"
        if confidence >= 0.5:
            return "Medium"
        return "Low"

    def _build_summary(
        self,
        records: List[Dict[str, Any]],
        anomalies: List[bool],
        stats: Dict[str, float],
    ) -> str:
        total = len(records)
        anomaly_count = sum(1 for a in anomalies if a)
        ratio = anomaly_count / total if total else 0.0
        return (
            f"Analyzed {total} windows; detected {anomaly_count} anomalies "
            f"({ratio:.1%}). Score range: {stats['min']:.4f}–{stats['max']:.4f}."
        )

    def _score_stats(self, scores: List[float]) -> Dict[str, float]:
        clean = [s for s in scores if s is not None]
        if not clean:
            return {"min": 0.0, "max": 0.0, "mean": 0.0}
        return {
            "min": min(clean),
            "max": max(clean),
            "mean": sum(clean) / len(clean),
        }

    def _is_anomaly(self, record: Dict[str, Any], stats: Dict[str, float]) -> bool:
        if "is_anomaly" in record:
            return bool(record.get("is_anomaly"))
        if "anomaly" in record:
            return int(record.get("anomaly")) == -1

        score = self._safe_float(record.get("score"))
        if stats["min"] == stats["max"]:
            return False
        threshold = stats["min"] + (stats["max"] - stats["min"]) * 0.2
        return score <= threshold

    def _safe_float(self, value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _to_dict(self, insight: Insight) -> Dict[str, Any]:
        return {
            "alert_type": insight.alert_type,
            "severity": insight.severity,
            "confidence": insight.confidence,
            "summary": insight.summary,
            "details": insight.details,
        }
