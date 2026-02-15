from typing import Dict, Any
from scapy.layers.inet import IP, TCP, UDP, ICMP


"""
Module providing helper functions for managing and updating
statistics of packet features within fixed time windows.

Classes:    
    WindowHelpers:
        A class containing static methods to create, update, and finalize
        statistics for packet feature windows.

Methods:
    new_window:
        Initializes a new statistics dictionary for a time window.

    update_window:
        Updates the statistics dictionary with data from a new packet.

    finalize_window:
        Finalizes and returns the statistics for a completed time window.

"""

class WindowHelpers:
    @staticmethod
    def new_window() -> Dict[str, Any]:
        return {
            "packet_count": 0,
            "total_bytes": 0,
            "tcp_count": 0,
            "udp_count": 0,
            "icmp_count": 0,
            "other_protocol_count": 0,
            "unique_src_ips": set(),
            "unique_dst_ips": set(),
            "flows": set(),
        }

    @staticmethod
    def update_window(pkt, stats: Dict[str, Any]) -> None:
        stats["packet_count"] += 1
        stats["total_bytes"] += len(pkt)

        ip = pkt[IP]
        stats["unique_src_ips"].add(ip.src)
        stats["unique_dst_ips"].add(ip.dst)

        src_port = None
        dst_port = None

        if pkt.haslayer(TCP):
            stats["tcp_count"] += 1
            src_port = pkt[TCP].sport
            dst_port = pkt[TCP].dport

        elif pkt.haslayer(UDP):
            stats["udp_count"] += 1
            src_port = pkt[UDP].sport
            dst_port = pkt[UDP].dport

        elif pkt.haslayer(ICMP):
            stats["icmp_count"] += 1

        else:
            stats["other_protocol_count"] += 1

        if src_port is not None and dst_port is not None:
            stats["flows"].add(
                (ip.src, src_port, ip.dst, dst_port, ip.proto)
            )

    @staticmethod
    def finalize_window(
        stats: Dict[str, Any],
        window_start: float,
        window_end: float
    ) -> Dict[str, Any]:
        duration = max(window_end - window_start, 1e-6)
        packet_count = stats["packet_count"]

        return {
            "window_start": window_start,
            "window_end": window_end,
            "duration": duration,
            "packet_count": packet_count,
            "total_bytes": stats["total_bytes"],
            "avg_packet_size": (
                stats["total_bytes"] / packet_count if packet_count else 0
            ),
            "bandwidth_bps": (stats["total_bytes"] * 8) / duration,
            "tcp_ratio": stats["tcp_count"] / packet_count if packet_count else 0,
            "udp_ratio": stats["udp_count"] / packet_count if packet_count else 0,
            "icmp_ratio": stats["icmp_count"] / packet_count if packet_count else 0,
            "unique_src_ip_count": len(stats["unique_src_ips"]),
            "unique_dst_ip_count": len(stats["unique_dst_ips"]),
            "flow_count": len(stats["flows"]),
        }
