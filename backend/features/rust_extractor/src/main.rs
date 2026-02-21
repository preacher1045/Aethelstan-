use pcap::Capture;
use etherparse::PacketHeaders;
use serde::Serialize;
use std::collections::{HashSet, HashMap};
use std::fs::File;
use std::net::{Ipv4Addr, Ipv6Addr};

// --------------------------
// Helper Functions
// --------------------------

/// Build packet size distribution histogram
fn build_packet_size_histogram(packet_sizes: &[usize]) -> HashMap<String, usize> {
    let mut histogram = HashMap::new();
    histogram.insert("64".to_string(), 0);
    histogram.insert("128".to_string(), 0);
    histogram.insert("256".to_string(), 0);
    histogram.insert("512".to_string(), 0);
    histogram.insert("1024".to_string(), 0);
    histogram.insert("1500".to_string(), 0);
    
    for &size in packet_sizes {
        if size <= 64 {
            *histogram.get_mut("64").unwrap() += 1;
        } else if size <= 128 {
            *histogram.get_mut("128").unwrap() += 1;
        } else if size <= 256 {
            *histogram.get_mut("256").unwrap() += 1;
        } else if size <= 512 {
            *histogram.get_mut("512").unwrap() += 1;
        } else if size <= 1024 {
            *histogram.get_mut("1024").unwrap() += 1;
        } else {
            *histogram.get_mut("1500").unwrap() += 1;
        }
    }
    
    histogram
}

type FlowKey = (String, u16, String, u16, String);
type PortKey = (u16, String);

#[derive(Clone)]
struct FlowAgg {
    packet_count: usize,
    total_bytes: usize,
    first_ts: f64,
    last_ts: f64,
}

#[derive(Clone)]
struct PortAgg {
    packet_count: usize,
    total_bytes: usize,
}

#[derive(Serialize, Clone)]
struct FlowStat {
    src_ip: String,
    dst_ip: String,
    src_port: u16,
    dst_port: u16,
    protocol: String,
    packet_count: usize,
    total_bytes: usize,
    duration_seconds: f64,
    start_timestamp: f64,
    end_timestamp: f64,
}

#[derive(Serialize, Clone)]
struct PortStat {
    port: u16,
    protocol: String,
    service_name: String,
    packet_count: usize,
    total_bytes: usize,
}

fn service_name_for_port(port: u16) -> &'static str {
    match port {
        80 => "HTTP",
        443 => "HTTPS",
        53 => "DNS",
        22 => "SSH",
        25 => "SMTP",
        110 => "POP3",
        143 => "IMAP",
        3389 => "RDP",
        3306 => "MySQL",
        5432 => "Postgres",
        _ => "Unknown",
    }
}

/// Build flow duration distribution histogram
fn build_flow_duration_histogram(flow_stats: &HashMap<FlowKey, FlowAgg>) -> HashMap<String, usize> {
    let mut histogram = HashMap::new();
    histogram.insert("0-5".to_string(), 0);
    histogram.insert("5-10".to_string(), 0);
    histogram.insert("10-20".to_string(), 0);
    histogram.insert("20-30".to_string(), 0);
    histogram.insert("30+".to_string(), 0);
    
    for agg in flow_stats.values() {
        let duration = (agg.last_ts - agg.first_ts).max(0.0);
        
        if duration <= 5.0 {
            *histogram.get_mut("0-5").unwrap() += 1;
        } else if duration <= 10.0 {
            *histogram.get_mut("5-10").unwrap() += 1;
        } else if duration <= 20.0 {
            *histogram.get_mut("10-20").unwrap() += 1;
        } else if duration <= 30.0 {
            *histogram.get_mut("20-30").unwrap() += 1;
        } else {
            *histogram.get_mut("30+").unwrap() += 1;
        }
    }
    
    histogram
}

fn build_top_flows(flow_stats: &HashMap<FlowKey, FlowAgg>, limit: usize) -> Vec<FlowStat> {
    let mut flows: Vec<FlowStat> = flow_stats
        .iter()
        .map(|(key, agg)| {
            let duration_seconds = (agg.last_ts - agg.first_ts).max(0.0);
            FlowStat {
                src_ip: key.0.clone(),
                src_port: key.1,
                dst_ip: key.2.clone(),
                dst_port: key.3,
                protocol: key.4.clone(),
                packet_count: agg.packet_count,
                total_bytes: agg.total_bytes,
                duration_seconds,
                start_timestamp: agg.first_ts,
                end_timestamp: agg.last_ts,
            }
        })
        .collect();

    flows.sort_by(|a, b| b.total_bytes.cmp(&a.total_bytes));
    flows.truncate(limit);
    flows
}

fn build_top_ports(port_stats: &HashMap<PortKey, PortAgg>, limit: usize) -> Vec<PortStat> {
    let mut ports: Vec<PortStat> = port_stats
        .iter()
        .map(|(key, agg)| PortStat {
            port: key.0,
            protocol: key.1.clone(),
            service_name: service_name_for_port(key.0).to_string(),
            packet_count: agg.packet_count,
            total_bytes: agg.total_bytes,
        })
        .collect();

    ports.sort_by(|a, b| b.total_bytes.cmp(&a.total_bytes));
    ports.truncate(limit);
    ports
}

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
    port_diversity: f64,
    // Phase 2: TCP Health Metrics
    tcp_syn_count: usize,
    tcp_ack_count: usize,
    tcp_rst_count: usize,
    tcp_fin_count: usize,
    tcp_retransmissions: usize,
    // Phase 2: Distribution Histograms
    packet_size_distribution: HashMap<String, usize>,
    flow_duration_distribution: HashMap<String, usize>,
    top_flows: Vec<FlowStat>,
    port_stats: Vec<PortStat>,
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
    let mut flow_stats: HashMap<FlowKey, FlowAgg> = HashMap::new();
    let mut port_stats: HashMap<PortKey, PortAgg> = HashMap::new();
    let mut window_features: Vec<WindowFeature> = Vec::new();
    
    // Phase 2: TCP Health Metrics counters
    let mut tcp_syn_count = 0;
    let mut tcp_ack_count = 0;
    let mut tcp_rst_count = 0;
    let mut tcp_fin_count = 0;
    let mut tcp_retransmissions = 0; // Placeholder - proper detection requires seq tracking
    
    // Phase 2: Flow duration tracking (stored in flow_stats)

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

            let flow_count = flow_stats.len();
            let flow_ratio = if packet_count > 0 { flow_count as f64 / packet_count as f64 } else { 0.0 };
            let avg_flow_packets = if flow_count > 0 { packet_count as f64 / flow_count as f64 } else { 0.0 };
            let avg_flow_bytes = if flow_count > 0 { total_bytes as f64 / flow_count as f64 } else { 0.0 };

            let packets_per_sec = packet_count as f64 / window_size;
            let bytes_per_sec = total_bytes as f64 / window_size; // bytes/sec

            let port_diversity = port_stats.len() as f64;

            // Phase 2: Build histograms
            let packet_size_distribution = build_packet_size_histogram(&packet_sizes);
            let flow_duration_distribution = build_flow_duration_histogram(&flow_stats);
            let top_flows = build_top_flows(&flow_stats, 10);
            let top_ports = build_top_ports(&port_stats, 10);

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
                flow_count,
                flow_ratio,
                avg_flow_packets,
                avg_flow_bytes,
                packets_per_sec,
                bytes_per_sec,
                port_diversity,
                tcp_syn_count,
                tcp_ack_count,
                tcp_rst_count,
                tcp_fin_count,
                tcp_retransmissions,
                packet_size_distribution,
                flow_duration_distribution,
                top_flows,
                port_stats: top_ports,
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
            flow_stats.clear();
            port_stats.clear();
            
            // Phase 2: Reset TCP health and flow tracking
            tcp_syn_count = 0;
            tcp_ack_count = 0;
            tcp_rst_count = 0;
            tcp_fin_count = 0;
            tcp_retransmissions = 0;

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
                        let flow_key = (src_ip.clone(), tcp.source_port, dst_ip.clone(), tcp.destination_port, "TCP".to_string());
                        let flow_entry = flow_stats.entry(flow_key).or_insert(FlowAgg {
                            packet_count: 0,
                            total_bytes: 0,
                            first_ts: timestamp,
                            last_ts: timestamp,
                        });
                        flow_entry.packet_count += 1;
                        flow_entry.total_bytes += packet.data.len();
                        flow_entry.last_ts = timestamp;

                        // Phase 2: Track TCP flags
                        if tcp.syn { tcp_syn_count += 1; }
                        if tcp.ack { tcp_ack_count += 1; }
                        if tcp.rst { tcp_rst_count += 1; }
                        if tcp.fin { tcp_fin_count += 1; }

                        let port_key = (tcp.destination_port, "TCP".to_string());
                        let port_entry = port_stats.entry(port_key).or_insert(PortAgg {
                            packet_count: 0,
                            total_bytes: 0,
                        });
                        port_entry.packet_count += 1;
                        port_entry.total_bytes += packet.data.len();
                    }
                    Some(etherparse::TransportHeader::Udp(udp)) => {
                        udp_count += 1;
                        let flow_key = (src_ip.clone(), udp.source_port, dst_ip.clone(), udp.destination_port, "UDP".to_string());
                        let flow_entry = flow_stats.entry(flow_key).or_insert(FlowAgg {
                            packet_count: 0,
                            total_bytes: 0,
                            first_ts: timestamp,
                            last_ts: timestamp,
                        });
                        flow_entry.packet_count += 1;
                        flow_entry.total_bytes += packet.data.len();
                        flow_entry.last_ts = timestamp;

                        let port_key = (udp.destination_port, "UDP".to_string());
                        let port_entry = port_stats.entry(port_key).or_insert(PortAgg {
                            packet_count: 0,
                            total_bytes: 0,
                        });
                        port_entry.packet_count += 1;
                        port_entry.total_bytes += packet.data.len();
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

        let flow_count = flow_stats.len();
        let flow_ratio = if packet_count > 0 { flow_count as f64 / packet_count as f64 } else { 0.0 };
        let avg_flow_packets = if flow_count > 0 { packet_count as f64 / flow_count as f64 } else { 0.0 };
        let avg_flow_bytes = if flow_count > 0 { total_bytes as f64 / flow_count as f64 } else { 0.0 };

        let packets_per_sec = packet_count as f64 / window_size;
        let bytes_per_sec = total_bytes as f64 / window_size; // bytes/sec

        let port_diversity = port_stats.len() as f64;

        // Phase 2: Build histograms for final window
        let packet_size_distribution = build_packet_size_histogram(&packet_sizes);
        let flow_duration_distribution = build_flow_duration_histogram(&flow_stats);
        let top_flows = build_top_flows(&flow_stats, 10);
        let top_ports = build_top_ports(&port_stats, 10);

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
            flow_count,
            flow_ratio,
            avg_flow_packets,
            avg_flow_bytes,
            packets_per_sec,
            bytes_per_sec,
            port_diversity,
            tcp_syn_count,
            tcp_ack_count,
            tcp_rst_count,
            tcp_fin_count,
            tcp_retransmissions,
            packet_size_distribution,
            flow_duration_distribution,
            top_flows,
            port_stats: top_ports,
        };
        window_features.push(window);
    }

    // Serialize to JSON
    window_features.serialize(&mut writer)?;
    println!("✅ Finished processing {} windows", window_features.len());

    Ok(())
}
