# Missing Data Analysis - Frontend Requirements vs Backend Schema

## 1. FLOW-LEVEL DATA (Top Flows Table)

**Frontend Needs (protocols/page.tsx):**
```typescript
{
  src: "10.0.1.24",           // Source IP
  dst: "172.16.1.8",          // Destination IP
  protocol: "TCP",            // Protocol name
  duration: "12s",            // Flow duration
  packets: 800,               // Packets in flow
  bytes: "3.2 MB"            // Bytes in flow
}
```

**Current Schema Has:**
- `unique_src_ips` (count only)
- `unique_dst_ips` (count only)
- `tcp_count`, `udp_count`, `icmp_count` (aggregated counts)

**Missing:**
- Individual flow records with source/dest IPs
- Per-flow packet counts
- Per-flow byte counts
- Per-flow duration

**Solution Options:**

### Option A: Add a new `flows` table
```sql
CREATE TABLE IF NOT EXISTS flows (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    window_id INTEGER NOT NULL,
    src_ip VARCHAR(45) NOT NULL,      -- IPv4/IPv6
    dst_ip VARCHAR(45) NOT NULL,
    src_port INTEGER,
    dst_port INTEGER,
    protocol VARCHAR(10) NOT NULL,     -- TCP, UDP, ICMP
    packet_count INTEGER NOT NULL,
    total_bytes BIGINT NOT NULL,
    duration_seconds DOUBLE PRECISION,
    start_timestamp DOUBLE PRECISION,
    end_timestamp DOUBLE PRECISION,
    
    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_flows_session ON flows(session_id);
CREATE INDEX IF NOT EXISTS idx_flows_window ON flows(session_id, window_id);
```

### Option B: Skip the Top Flows feature entirely
Remove the feature from the frontend since your current analysis is window-based, not flow-based.

---

## 2. PROTOCOL DISTRIBUTION OVER TIME

**Frontend Needs (sessions/[sessionId]/page.tsx):**
```typescript
protocolSeries = [
  { tcp: 45, udp: 30, icmp: 12 },  // Window 1
  { tcp: 52, udp: 25, icmp: 10 },  // Window 2
  { tcp: 48, udp: 28, icmp: 11 },  // Window 3
  // ... for each time window
]
```

**Current Schema Has:**
In `traffic_windows` table:
- `tcp_ratio` ✅
- `udp_ratio` ✅
- `icmp_ratio` ✅

**Status: ✅ DATA EXISTS**

**Fix:** Just map the real data in frontend instead of generating fake data.

```typescript
// CORRECT implementation
const protocolSeries = useMemo(() => {
  return results.map(window => ({
    tcp: window.tcp_ratio ?? 0,
    udp: window.udp_ratio ?? 0,
    icmp: window.icmp_ratio ?? 0,
  }));
}, [results]);
```

---

## 3. TOP TALKERS (Top IPs by Traffic Volume)

**Frontend Needs (sessions/[sessionId]/page.tsx):**
```typescript
{
  ip: "10.0.1.24",           // IP address
  bytes: 120,                 // Total GB transferred
  share: 85                   // Percentage of total traffic
}
```

**Current Schema Has:**
- Only counts: `unique_src_ips`, `unique_dst_ips`

**Missing:**
- Individual IP addresses
- Per-IP byte counts

**Solution Options:**

### Option A: Add `top_ips` table
```sql
CREATE TABLE IF NOT EXISTS top_ips (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45) NOT NULL,
    total_bytes BIGINT NOT NULL,
    total_packets INTEGER NOT NULL,
    direction VARCHAR(10),              -- 'src', 'dst', or 'both'
    
    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_top_ips_session ON top_ips(session_id);
```

### Option B: Add JSONB column to `pcap_sessions`
```sql
ALTER TABLE pcap_sessions ADD COLUMN top_talkers JSONB;

-- Populated with:
{
  "top_src_ips": [
    {"ip": "10.0.1.24", "bytes": 120000000, "packets": 80000},
    ...
  ],
  "top_dst_ips": [
    {"ip": "172.16.1.8", "bytes": 95000000, "packets": 65000},
    ...
  ]
}
```

### Option C: Remove Top Talkers feature
If you don't need IP-level analysis, remove the UI component.

---

## 4. TCP HEALTH METRICS

**Frontend Needs (protocols/page.tsx):**
```typescript
{
  syn_ack_ratio: "1.08",
  rst_rate: "2.4%",
  retransmission_rate: "0.9%"
}
```

**Current Schema Has:**
- Nothing related to TCP flags or retransmissions

**Missing:**
- SYN count
- ACK count
- RST count
- Retransmission count
- Total TCP packets

**Solution:**

Add columns to `traffic_windows` table:
```sql
ALTER TABLE traffic_windows ADD COLUMN tcp_syn_count INTEGER DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN tcp_ack_count INTEGER DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN tcp_rst_count INTEGER DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN tcp_fin_count INTEGER DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN tcp_retransmissions INTEGER DEFAULT 0;
```

**OR** add to `features_json` JSONB field (already exists):
```json
{
  "tcp_syn_count": 1200,
  "tcp_ack_count": 1150,
  "tcp_rst_count": 28,
  "tcp_retransmissions": 15
}
```

---

## 5. PORT USAGE DISTRIBUTION

**Frontend Needs (protocols/page.tsx):**
```typescript
{
  port: "443 (HTTPS)",
  percentage: 32,
  count: 15000
}
```

**Current Schema Has:**
- `port_diversity` (aggregate metric only)

**Missing:**
- Individual port counts
- Top ports by traffic volume

**Solution:**

Add `port_stats` table:
```sql
CREATE TABLE IF NOT EXISTS port_stats (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL,
    service_name VARCHAR(50),           -- 'HTTPS', 'HTTP', 'SSH', etc.
    packet_count INTEGER NOT NULL,
    byte_count BIGINT NOT NULL,
    
    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_port_stats_session ON port_stats(session_id);
```

**OR** add to session-level JSONB:
```sql
ALTER TABLE pcap_sessions ADD COLUMN port_distribution JSONB;

-- Example:
{
  "443": {"service": "HTTPS", "packets": 150000, "bytes": 98000000},
  "80": {"service": "HTTP", "packets": 85000, "bytes": 45000000},
  "53": {"service": "DNS", "packets": 12000, "bytes": 2000000}
}
```

---

## 6. PACKET SIZE DISTRIBUTION

**Frontend Needs (traffic/page.tsx):**
```typescript
packetHistogram = [25, 45, 78, 92, 65, 42, 38, 55, 70, 48]
// Distribution across size buckets: 64B, 512B, 1KB, etc.
```

**Current Schema Has:**
- `avg_packet_size` ✅
- `min_packet_size` ✅
- `max_packet_size` ✅
- `packet_size_std` ✅

**Missing:**
- Histogram buckets (distribution across size ranges)

**Solution:**

Add to `traffic_windows`:
```sql
ALTER TABLE traffic_windows ADD COLUMN packet_size_distribution JSONB;

-- Example:
{
  "64": 150,      // 150 packets <= 64 bytes
  "128": 320,     // 320 packets 65-128 bytes
  "256": 580,     // etc.
  "512": 1200,
  "1024": 2500,
  "1500": 3200
}
```

---

## 7. FLOW DURATION DISTRIBUTION

**Frontend Needs (traffic/page.tsx):**
```typescript
flowHistogram = [20, 35, 45, 60, 75, 82, 68, 55, 42, 30, 25, 18]
// Distribution: 0-5s, 5-10s, 10-15s, etc.
```

**Current Schema Has:**
- Nothing about flow duration distribution

**Missing:**
- Flow duration histogram

**Solution:**

Add to `traffic_windows`:
```sql
ALTER TABLE traffic_windows ADD COLUMN flow_duration_distribution JSONB;

-- Example:
{
  "0-5": 450,      // 450 flows lasted 0-5 seconds
  "5-10": 320,
  "10-20": 180,
  "20-30": 95,
  "30+": 55
}
```

---

## 8. THROUGHPUT HEATMAP DATA

**Frontend Needs (traffic/page.tsx):**
```typescript
// 96 data points (4 per hour × 24 hours) showing volume intensity
heatmapData = [
  0.2, 0.3, 0.4, 0.5, ... // 96 values between 0-1
]
```

**Current Schema Has:**
- `bytes_per_sec` (per window) ✅

**Status: ✅ DATA EXISTS**

**Fix:** Map real data from `traffic_windows.bytes_per_sec`

```typescript
const heatmapData = results.map(w => w.bytes_per_sec ?? 0);
```

---

## 9. INBOUND VS OUTBOUND TRAFFIC

**Frontend Needs (traffic/page.tsx):**
```typescript
{
  inbound_percentage: 62,
  outbound_percentage: 38,
  inbound_bytes: 520000000,
  outbound_bytes: 320000000
}
```

**Current Schema Has:**
- Nothing about traffic direction

**Missing:**
- Inbound byte count
- Outbound byte count

**Solution:**

Add to `traffic_windows`:
```sql
ALTER TABLE traffic_windows ADD COLUMN inbound_bytes BIGINT DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN outbound_bytes BIGINT DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN inbound_packets INTEGER DEFAULT 0;
ALTER TABLE traffic_windows ADD COLUMN outbound_packets INTEGER DEFAULT 0;
```

**Note:** This requires the Rust extractor to track direction. You'll need a reference IP or subnet to determine what's "inbound" vs "outbound".

---

## 10. EVENT MARKERS / BURST DETECTION

**Frontend Needs (timeline/page.tsx):**
```typescript
{
  timestamp: "14:07:23",
  event_type: "Anomaly burst",
  description: "Unusual spike in short-lived connections",
  severity: "high"
}
```

**Current Schema Has:**
- Anomaly results per window ✅
- Insights with alerts ✅

**Status: ✅ DATA EXISTS (partially)**

**Fix:** Extract from existing `insights` table:

```typescript
const eventMarkers = insights
  .filter(i => i.insight_type === 'alert')
  .map(i => ({
    timestamp: new Date(i.created_at).toLocaleTimeString(),
    event_type: i.alert_type,
    description: i.summary,
    severity: i.severity
  }));
```

---

## 11. FEATURE CONTRIBUTION (ML Explainability)

**Frontend Needs (anomalies/page.tsx):**
```typescript
{
  feature: "Connection rate",
  importance: 80  // percentage contribution
}
```

**Current Schema Has:**
- `contributing_features` JSONB in `anomaly_results` ✅

**Status: ✅ DATA EXISTS (if populated by ML model)**

**Fix:** Make sure your ML inference code populates this field:

```python
# In production_inference.py or inference.py
contributing_features = {
  "connection_rate": 0.85,
  "packet_size_variance": 0.72,
  "unique_dst_ips": 0.68,
  "port_diversity": 0.65
}
```

---

## SUMMARY TABLE

| Feature | Schema Has It? | Action Required |
|---------|----------------|-----------------|
| Protocol distribution over time | ✅ Yes | Map real data in frontend |
| Anomaly score timeline | ✅ Yes | Map real data in frontend |
| Throughput over time | ✅ Yes | Map real data in frontend |
| Feature contribution | ✅ Yes (if ML populates) | Ensure ML model outputs it |
| Event markers | ✅ Yes (from insights) | Map real data in frontend |
| **Top Flows (src/dst IPs)** | ❌ No | Add `flows` table OR remove feature |
| **Top Talkers (IP rankings)** | ❌ No | Add `top_ips` table OR remove feature |
| **TCP Health Metrics** | ❌ No | Add columns to `traffic_windows` |
| **Port Distribution** | ❌ No | Add `port_stats` table OR JSONB |
| **Packet Size Distribution** | ❌ No | Add JSONB histogram to `traffic_windows` |
| **Flow Duration Distribution** | ❌ No | Add JSONB histogram to `traffic_windows` |
| **Inbound/Outbound Split** | ❌ No | Add columns to `traffic_windows` |

---

