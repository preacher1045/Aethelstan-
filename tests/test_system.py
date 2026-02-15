"""
End-to-end system test: Extract features from new PCAP → Detect anomalies
"""

import subprocess
import json
import pandas as pd
from pathlib import Path
from backend.ml.inference import AnomalyPredictor
from scripts.data_cleanup import clean_and_engineer_features, select_features

print("=" * 70)
print("NETWORK ANOMALY DETECTION - FULL SYSTEM TEST")
print("=" * 70)

# Step 1: Check if pcapng needs conversion
pcap_file = "data/raw/test_net_traffic.pcapng"
output_features = "data/processed/test_net_traffic_features.json"

print(f"\n📂 Input: {pcap_file}")
print(f"📂 Output: {output_features}")

# Check if we need to convert pcapng to pcap
if pcap_file.endswith('.pcapng'):
    print("\n⚠️  PCAPNG format detected. Converting to PCAP format...")
    converted_pcap = pcap_file.replace('.pcapng', '_converted.pcap')
    
    # Try using tshark/editcap if available, otherwise use Python
    try:
        result = subprocess.run(
            ['editcap', '-F', 'pcap', pcap_file, converted_pcap],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"✅ Converted to {converted_pcap}")
            pcap_file = converted_pcap
        else:
            print("⚠️  editcap not available. Trying Python conversion...")
            raise FileNotFoundError
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # Use Python to convert
        print("⚠️  Using Python-based feature extraction instead...")
        
        # Let's use scapy to read the pcapng and extract features directly
        try:
            from scapy.all import rdpcap, IP, TCP, UDP, ICMP
            import time
            
            print("\n🔍 Step 1: Extracting features using Python...")
            packets = rdpcap(pcap_file)
            print(f"   Loaded {len(packets)} packets")
            
            # Window-based feature extraction
            window_size = 60.0  # seconds
            windows = []
            
            if len(packets) > 0:
                start_time = float(packets[0].time)
                current_window = {
                    'window_start': start_time,
                    'window_end': start_time + window_size,
                    'packet_count': 0,
                    'total_bytes': 0,
                    'packet_sizes': [],
                    'tcp_count': 0,
                    'udp_count': 0,
                    'icmp_count': 0,
                    'other_count': 0,
                    'src_ips': set(),
                    'dst_ips': set(),
                    'flows': set()
                }
                
                for i, pkt in enumerate(packets):
                    if i % 10000 == 0 and i > 0:
                        print(f"   Processed {i} packets...")
                    
                    pkt_time = float(pkt.time)
                    
                    # Check if we need a new window
                    while pkt_time > current_window['window_end']:
                        # Finalize current window
                        if current_window['packet_count'] > 0:
                            avg_size = current_window['total_bytes'] / current_window['packet_count']
                            window_feature = {
                                'window_start': current_window['window_start'],
                                'window_end': current_window['window_end'],
                                'packet_count': current_window['packet_count'],
                                'total_bytes': current_window['total_bytes'],
                                'avg_packet_size': avg_size,
                                'min_packet_size': min(current_window['packet_sizes']) if current_window['packet_sizes'] else 0,
                                'max_packet_size': max(current_window['packet_sizes']) if current_window['packet_sizes'] else 0,
                                'packet_size_std': pd.Series(current_window['packet_sizes']).std() if current_window['packet_sizes'] else 0,
                                'tcp_count': current_window['tcp_count'],
                                'udp_count': current_window['udp_count'],
                                'icmp_count': current_window['icmp_count'],
                                'other_count': current_window['other_count'],
                                'tcp_ratio': current_window['tcp_count'] / current_window['packet_count'],
                                'udp_ratio': current_window['udp_count'] / current_window['packet_count'],
                                'icmp_ratio': current_window['icmp_count'] / current_window['packet_count'],
                                'other_ratio': current_window['other_count'] / current_window['packet_count'],
                                'unique_src_ips': len(current_window['src_ips']),
                                'unique_dst_ips': len(current_window['dst_ips']),
                                'unique_src_ratio': len(current_window['src_ips']) / current_window['packet_count'],
                                'unique_dst_ratio': len(current_window['dst_ips']) / current_window['packet_count'],
                                'flow_count': len(current_window['flows']),
                                'flow_ratio': len(current_window['flows']) / current_window['packet_count'],
                                'avg_flow_packets': current_window['packet_count'] / len(current_window['flows']) if current_window['flows'] else 0,
                                'avg_flow_bytes': current_window['total_bytes'] / len(current_window['flows']) if current_window['flows'] else 0,
                                'packets_per_sec': current_window['packet_count'] / window_size,
                                'bytes_per_sec': current_window['total_bytes'] / window_size
                            }
                            windows.append(window_feature)
                        
                        # Start new window
                        current_window = {
                            'window_start': current_window['window_end'],
                            'window_end': current_window['window_end'] + window_size,
                            'packet_count': 0,
                            'total_bytes': 0,
                            'packet_sizes': [],
                            'tcp_count': 0,
                            'udp_count': 0,
                            'icmp_count': 0,
                            'other_count': 0,
                            'src_ips': set(),
                            'dst_ips': set(),
                            'flows': set()
                        }
                    
                    # Process packet
                    pkt_len = len(pkt)
                    current_window['packet_count'] += 1
                    current_window['total_bytes'] += pkt_len
                    current_window['packet_sizes'].append(pkt_len)
                    
                    if IP in pkt:
                        src_ip = pkt[IP].src
                        dst_ip = pkt[IP].dst
                        current_window['src_ips'].add(src_ip)
                        current_window['dst_ips'].add(dst_ip)
                        
                        proto = "other"
                        sport = 0
                        dport = 0
                        
                        if TCP in pkt:
                            current_window['tcp_count'] += 1
                            proto = "TCP"
                            sport = pkt[TCP].sport
                            dport = pkt[TCP].dport
                        elif UDP in pkt:
                            current_window['udp_count'] += 1
                            proto = "UDP"
                            sport = pkt[UDP].sport
                            dport = pkt[UDP].dport
                        elif ICMP in pkt:
                            current_window['icmp_count'] += 1
                            proto = "ICMP"
                        else:
                            current_window['other_count'] += 1
                        
                        if sport and dport:
                            current_window['flows'].add((src_ip, sport, dst_ip, dport, proto))
                
                # Add last window
                if current_window['packet_count'] > 0:
                    avg_size = current_window['total_bytes'] / current_window['packet_count']
                    window_feature = {
                        'window_start': current_window['window_start'],
                        'window_end': current_window['window_end'],
                        'packet_count': current_window['packet_count'],
                        'total_bytes': current_window['total_bytes'],
                        'avg_packet_size': avg_size,
                        'min_packet_size': min(current_window['packet_sizes']) if current_window['packet_sizes'] else 0,
                        'max_packet_size': max(current_window['packet_sizes']) if current_window['packet_sizes'] else 0,
                        'packet_size_std': pd.Series(current_window['packet_sizes']).std() if current_window['packet_sizes'] else 0,
                        'tcp_count': current_window['tcp_count'],
                        'udp_count': current_window['udp_count'],
                        'icmp_count': current_window['icmp_count'],
                        'other_count': current_window['other_count'],
                        'tcp_ratio': current_window['tcp_count'] / current_window['packet_count'],
                        'udp_ratio': current_window['udp_count'] / current_window['packet_count'],
                        'icmp_ratio': current_window['icmp_count'] / current_window['packet_count'],
                        'other_ratio': current_window['other_count'] / current_window['packet_count'],
                        'unique_src_ips': len(current_window['src_ips']),
                        'unique_dst_ips': len(current_window['dst_ips']),
                        'unique_src_ratio': len(current_window['src_ips']) / current_window['packet_count'],
                        'unique_dst_ratio': len(current_window['dst_ips']) / current_window['packet_count'],
                        'flow_count': len(current_window['flows']),
                        'flow_ratio': len(current_window['flows']) / current_window['packet_count'],
                        'avg_flow_packets': current_window['packet_count'] / len(current_window['flows']) if current_window['flows'] else 0,
                        'avg_flow_bytes': current_window['total_bytes'] / len(current_window['flows']) if current_window['flows'] else 0,
                        'packets_per_sec': current_window['packet_count'] / window_size,
                        'bytes_per_sec': current_window['total_bytes'] / window_size
                    }
                    windows.append(window_feature)
                
                # Save features
                Path(output_features).parent.mkdir(parents=True, exist_ok=True)
                with open(output_features, 'w') as f:
                    json.dump(windows, f, indent=2)
                
                print(f"✅ Extracted {len(windows)} windows")
                print(f"✅ Features saved to {output_features}")
                
        except ImportError:
            print("❌ ERROR: scapy not installed. Install with: pip install scapy")
            exit(1)
        except Exception as e:
            print(f"❌ ERROR extracting features: {e}")
            exit(1)

# Step 2: Load and clean features
print("\n🧹 Step 2: Cleaning and engineering features...")
with open(output_features, 'r') as f:
    raw_features = json.load(f)

df = pd.DataFrame(raw_features)
print(f"   Raw features shape: {df.shape}")

df = clean_and_engineer_features(df)
df = select_features(df)
print(f"   Cleaned features shape: {df.shape}")

# Step 3: Load model and predict
print("\n🤖 Step 3: Loading model and detecting anomalies...")
predictor = AnomalyPredictor('models/network_anomaly_model.pkl')

results = predictor.predict_from_features(df)

# Step 4: Display results
print("\n" + "=" * 70)
print("ANOMALY DETECTION RESULTS")
print("=" * 70)
print(f"Total windows analyzed: {len(df)}")
print(f"Anomalies detected: {results['anomaly_count']}")
print(f"Anomaly ratio: {results['anomaly_ratio']:.2%}")
print("=" * 70)

# Show top anomalies
labeled_df = predictor.predict_and_label(df)
top_anomalies = predictor.get_top_anomalies(df, top_n=min(10, len(df)))

print("\n🚨 Top Anomalous Windows:")
print("-" * 70)
for idx, row in top_anomalies.iterrows():
    status = "⚠️  ANOMALY" if row['is_anomaly'] else "ℹ️  Suspicious"
    print(f"{status} | Score: {row['score']:.4f} | Packets: {row['packet_count']:,} | "
          f"TCP: {row['tcp_ratio']:.2%} | Bytes/sec: {row['bytes_per_sec']:,.0f}")

print("\n" + "=" * 70)
print("✅ SYSTEM TEST COMPLETE")
print("=" * 70)
