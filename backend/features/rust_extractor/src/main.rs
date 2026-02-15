use pcap::Capture;
use etherparse::PacketHeaders;
use serde::Serialize;
use std::collections::HashSet;
use std::fs::File;
use std::net::{Ipv4Addr, Ipv6Addr};

// --------------------------
// Window Feature Structure
// --------------------------
#[derive(Serialize)]
struct WindowFeature {
    window_start: f64,
    window_end: f64,
    packet_count: usize,
    total_bytes: usize,
    avg_packet_size: f64,
    min_packet_size: usize,
    max_packet_size: usize,
    packet_size_std: f64,
    tcp_count: usize,
    udp_count: usize,
    icmp_count: usize,
    other_count: usize,
    tcp_ratio: f64,
    udp_ratio: f64,
    icmp_ratio: f64,
    other_ratio: f64,
    unique_src_ips: usize,
    unique_dst_ips: usize,
    unique_src_ratio: f64,
    unique_dst_ratio: f64,
    flow_count: usize,
    flow_ratio: f64,
    avg_flow_packets: f64,
    avg_flow_bytes: f64,
    packets_per_sec: f64,
    bytes_per_sec: f64,
}

// --------------------------
// Main Function
// --------------------------
fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get command-line arguments
    let args: Vec<String> = std::env::args().collect();
    
    let (pcap_file, output_path) = if args.len() >= 3 {
        // Use command-line arguments
        (args[1].clone(), args[2].clone())
    } else {
        // Fallback to hardcoded paths
        ("data/raw/2023_test.pcap".to_string(), "data/processed/2023_test_features.json".to_string())
    };
    
    let output_file = File::create(&output_path)?;
    let mut writer = serde_json::Serializer::pretty(output_file);

    let mut cap = Capture::from_file(&pcap_file)?;
    let window_size = 10.0; // seconds - REDUCED from 60s to get more training windows
    let mut window_start: Option<f64> = None;
    let mut window_end: f64 = 0.0;

    // Counters
    let mut packet_count = 0;
    let mut total_bytes = 0;
    let mut tcp_count = 0;
    let mut udp_count = 0;
    let mut icmp_count = 0;
    let mut other_count = 0;
    let mut packet_sizes: Vec<usize> = Vec::new();
    let mut unique_src_ips: HashSet<String> = HashSet::new();
    let mut unique_dst_ips: HashSet<String> = HashSet::new();
    let mut flows: HashSet<(String, u16, String, u16, String)> = HashSet::new();
    let mut window_features: Vec<WindowFeature> = Vec::new();

    while let Some(packet) = cap.next_packet().ok() {
        let ts = packet.header.ts;
        let timestamp = ts.tv_sec as f64 + ts.tv_usec as f64 * 1e-6;

        if window_start.is_none() {
            window_start = Some(timestamp);
            window_end = window_start.unwrap() + window_size;
        }

        if timestamp > window_end {
            // finalize current window
            let avg_packet_size = if packet_count > 0 {
                total_bytes as f64 / packet_count as f64
            } else { 0.0 };
            let min_packet_size = *packet_sizes.iter().min().unwrap_or(&0);
            let max_packet_size = *packet_sizes.iter().max().unwrap_or(&0);
            let packet_size_std = if packet_count > 0 {
                let mean = avg_packet_size;
                (packet_sizes.iter().map(|&s| (s as f64 - mean).powi(2)).sum::<f64>() / packet_count as f64).sqrt()
            } else { 0.0 };

            let tcp_ratio = if packet_count > 0 { tcp_count as f64 / packet_count as f64 } else { 0.0 };
            let udp_ratio = if packet_count > 0 { udp_count as f64 / packet_count as f64 } else { 0.0 };
            let icmp_ratio = if packet_count > 0 { icmp_count as f64 / packet_count as f64 } else { 0.0 };
            let other_ratio = if packet_count > 0 { other_count as f64 / packet_count as f64 } else { 0.0 };

            let unique_src_ratio = if packet_count > 0 { unique_src_ips.len() as f64 / packet_count as f64 } else { 0.0 };
            let unique_dst_ratio = if packet_count > 0 { unique_dst_ips.len() as f64 / packet_count as f64 } else { 0.0 };

            let flow_ratio = if packet_count > 0 { flows.len() as f64 / packet_count as f64 } else { 0.0 };
            let avg_flow_packets = if flows.len() > 0 { packet_count as f64 / flows.len() as f64 } else { 0.0 };
            let avg_flow_bytes = if flows.len() > 0 { total_bytes as f64 / flows.len() as f64 } else { 0.0 };

            let packets_per_sec = packet_count as f64 / window_size;
            let bytes_per_sec = total_bytes as f64 * 8.0 / window_size; // bits/sec

            let window = WindowFeature {
                window_start: window_start.unwrap(),
                window_end,
                packet_count,
                total_bytes,
                avg_packet_size,
                min_packet_size,
                max_packet_size,
                packet_size_std,
                tcp_count,
                udp_count,
                icmp_count,
                other_count,
                tcp_ratio,
                udp_ratio,
                icmp_ratio,
                other_ratio,
                unique_src_ips: unique_src_ips.len(),
                unique_dst_ips: unique_dst_ips.len(),
                unique_src_ratio,
                unique_dst_ratio,
                flow_count: flows.len(),
                flow_ratio,
                avg_flow_packets,
                avg_flow_bytes,
                packets_per_sec,
                bytes_per_sec,
            };
            window_features.push(window);

            // reset counters
            packet_count = 0;
            total_bytes = 0;
            tcp_count = 0;
            udp_count = 0;
            icmp_count = 0;
            other_count = 0;
            packet_sizes.clear();
            unique_src_ips.clear();
            unique_dst_ips.clear();
            flows.clear();

            window_start = Some(timestamp);
            window_end = window_start.unwrap() + window_size;
        }

        packet_count += 1;
        total_bytes += packet.data.len();
        packet_sizes.push(packet.data.len());

        // parse headers using etherparse
        if let Ok(headers) = PacketHeaders::from_ethernet_slice(&packet.data) {
            if let Some(ip) = headers.ip {
                let (src_ip, dst_ip) = match ip {
                    etherparse::IpHeader::Version4(header, _) => {
                        (Ipv4Addr::from(header.source).to_string(),
                        Ipv4Addr::from(header.destination).to_string())
                    }
                    etherparse::IpHeader::Version6(header, _) => {
                        (Ipv6Addr::from(header.source).to_string(),
                        Ipv6Addr::from(header.destination).to_string())
                    }
                };

                unique_src_ips.insert(src_ip.clone());
                unique_dst_ips.insert(dst_ip.clone());

                match headers.transport {
                    Some(etherparse::TransportHeader::Tcp(tcp)) => {
                        tcp_count += 1;
                        flows.insert((src_ip, tcp.source_port, dst_ip, tcp.destination_port, "TCP".to_string()));
                    }
                    Some(etherparse::TransportHeader::Udp(udp)) => {
                        udp_count += 1;
                        flows.insert((src_ip, udp.source_port, dst_ip, udp.destination_port, "UDP".to_string()));
                    }
                    Some(etherparse::TransportHeader::Icmpv4(_)) |
                    Some(etherparse::TransportHeader::Icmpv6(_)) => {
                        icmp_count += 1;
                    }
                    _ => { other_count += 1; }
                }
            } else {
                other_count += 1; // non-IP packet
            }
        } else {
            other_count += 1; // failed parsing
        }

        if packet_count % 500_000 == 0 {
            println!("Processed {} packets...", packet_count);
        }
    }

    // Flush last window
    if packet_count > 0 {
        let avg_packet_size = if packet_count > 0 { total_bytes as f64 / packet_count as f64 } else { 0.0 };
        let min_packet_size = *packet_sizes.iter().min().unwrap_or(&0);
        let max_packet_size = *packet_sizes.iter().max().unwrap_or(&0);
        let packet_size_std = if packet_count > 0 {
            let mean = avg_packet_size;
            (packet_sizes.iter().map(|&s| (s as f64 - mean).powi(2)).sum::<f64>() / packet_count as f64).sqrt()
        } else { 0.0 };

        let tcp_ratio = if packet_count > 0 { tcp_count as f64 / packet_count as f64 } else { 0.0 };
        let udp_ratio = if packet_count > 0 { udp_count as f64 / packet_count as f64 } else { 0.0 };
        let icmp_ratio = if packet_count > 0 { icmp_count as f64 / packet_count as f64 } else { 0.0 };
        let other_ratio = if packet_count > 0 { other_count as f64 / packet_count as f64 } else { 0.0 };

        let unique_src_ratio = if packet_count > 0 { unique_src_ips.len() as f64 / packet_count as f64 } else { 0.0 };
        let unique_dst_ratio = if packet_count > 0 { unique_dst_ips.len() as f64 / packet_count as f64 } else { 0.0 };

        let flow_ratio = if packet_count > 0 { flows.len() as f64 / packet_count as f64 } else { 0.0 };
        let avg_flow_packets = if flows.len() > 0 { packet_count as f64 / flows.len() as f64 } else { 0.0 };
        let avg_flow_bytes = if flows.len() > 0 { total_bytes as f64 / flows.len() as f64 } else { 0.0 };

        let packets_per_sec = packet_count as f64 / window_size;
        let bytes_per_sec = total_bytes as f64 * 8.0 / window_size; // bits/sec

        let window = WindowFeature {
            window_start: window_start.unwrap(),
            window_end,
            packet_count,
            total_bytes,
            avg_packet_size,
            min_packet_size,
            max_packet_size,
            packet_size_std,
            tcp_count,
            udp_count,
            icmp_count,
            other_count,
            tcp_ratio,
            udp_ratio,
            icmp_ratio,
            other_ratio,
            unique_src_ips: unique_src_ips.len(),
            unique_dst_ips: unique_dst_ips.len(),
            unique_src_ratio,
            unique_dst_ratio,
            flow_count: flows.len(),
            flow_ratio,
            avg_flow_packets,
            avg_flow_bytes,
            packets_per_sec,
            bytes_per_sec,
        };
        window_features.push(window);
    }

    // Serialize to JSON
    window_features.serialize(&mut writer)?;
    println!("✅ Finished processing {} windows", window_features.len());

    Ok(())
}
