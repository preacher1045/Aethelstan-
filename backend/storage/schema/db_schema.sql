-- =============================================================================
-- Full Database Schema
-- Creation order: pcap_sessions → traffic_windows → anomaly_results → insights
-- This file defines the complete database schema for the network traffic analysis application.
-- It includes all tables, relationships, and essential indexes for efficient querying.
-- Note: This schema is designed for PostgreSQL and may require adjustments for other databases.
--Schema must be run squencially using "alt+z" to maintain foreign key dependencies
--Created at: 2024-06-01 12:00 PM
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. PCAP Sessions Table
-- Stores information about each PCAP file processing session
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pcap_sessions (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    filename VARCHAR(500) NOT NULL,
    filepath TEXT,
    file_size_bytes BIGINT,
    total_packets INTEGER,
    start_timestamp DOUBLE PRECISION,
    end_timestamp DOUBLE PRECISION,
    duration_seconds DOUBLE PRECISION,
    status VARCHAR(50) DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_pcap_status ON pcap_sessions(status) WHERE status IN ('processing', 'pending');
CREATE INDEX IF NOT EXISTS idx_pcap_created_at ON pcap_sessions(created_at DESC);


-- -----------------------------------------------------------------------------
-- 2. Traffic Windows Table
-- Stores extracted features for each time window from network traffic
-- Depends on: pcap_sessions
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS traffic_windows (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    window_id INTEGER NOT NULL,
    window_start DOUBLE PRECISION NOT NULL,
    window_end DOUBLE PRECISION NOT NULL,

    -- Packet Statistics
    packet_count INTEGER NOT NULL,
    total_bytes BIGINT NOT NULL,
    avg_packet_size DOUBLE PRECISION,
    min_packet_size INTEGER,
    max_packet_size INTEGER,
    packet_size_std DOUBLE PRECISION,

    -- Protocol Distribution
    tcp_count INTEGER DEFAULT 0,
    udp_count INTEGER DEFAULT 0,
    icmp_count INTEGER DEFAULT 0,
    other_count INTEGER DEFAULT 0,
    tcp_ratio DOUBLE PRECISION DEFAULT 0.0,
    udp_ratio DOUBLE PRECISION DEFAULT 0.0,
    icmp_ratio DOUBLE PRECISION DEFAULT 0.0,
    other_ratio DOUBLE PRECISION DEFAULT 0.0,

    -- Network Topology
    unique_src_ips INTEGER,
    unique_dst_ips INTEGER,
    unique_src_ratio DOUBLE PRECISION,
    unique_dst_ratio DOUBLE PRECISION,

    -- Flow Statistics
    flow_count INTEGER,
    flow_ratio DOUBLE PRECISION,
    avg_flow_packets DOUBLE PRECISION,
    avg_flow_bytes DOUBLE PRECISION,

    -- Rate Metrics
    packets_per_sec DOUBLE PRECISION,
    bytes_per_sec DOUBLE PRECISION,

    -- Behavioral Features
    port_diversity DOUBLE PRECISION,
    avg_inter_arrival_time DOUBLE PRECISION,
    connection_rate DOUBLE PRECISION,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    features_json JSONB,

    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_window_session ON traffic_windows(session_id);
CREATE INDEX IF NOT EXISTS idx_window_composite ON traffic_windows(session_id, window_id);


-- -----------------------------------------------------------------------------
-- 3. Anomaly Results Table
-- Stores anomaly detection results for each traffic window
-- Depends on: pcap_sessions, traffic_windows
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS anomaly_results (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    window_id INTEGER NOT NULL,
    traffic_window_id INTEGER,

    -- Anomaly Detection Results
    is_anomaly BOOLEAN NOT NULL DEFAULT false,
    anomaly_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION,
    prediction_label VARCHAR(50), -- normal, anomaly, suspicious

    -- Model Information
    model_name VARCHAR(100),
    model_version VARCHAR(50),
    threshold_used DOUBLE PRECISION,

    -- Deviation Metrics
    baseline_deviation DOUBLE PRECISION,
    severity_level VARCHAR(20), -- low, medium, high, critical

    -- Analysis Details
    contributing_features JSONB,
    anomaly_type VARCHAR(100), -- volume_spike, protocol_anomaly, scan_detected
    tags JSONB,

    -- Processing Metadata
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_time_ms DOUBLE PRECISION,

    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (traffic_window_id) REFERENCES traffic_windows(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_anomaly_session ON anomaly_results(session_id);
CREATE INDEX IF NOT EXISTS idx_anomaly_flag ON anomaly_results(is_anomaly) WHERE is_anomaly = true;
CREATE INDEX IF NOT EXISTS idx_anomaly_severity ON anomaly_results(severity_level) WHERE severity_level IN ('high', 'critical');


-- -----------------------------------------------------------------------------
-- 4. Insights Table
-- Stores human-readable insights and alerts generated from anomaly analysis
-- Depends on: pcap_sessions, anomaly_results
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS insights (
    id SERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    insight_type VARCHAR(100) NOT NULL, -- alert, summary, recommendation, pattern

    -- Alert Information
    alert_type VARCHAR(150),
    severity VARCHAR(20), -- Critical, High, Medium, Low
    confidence DOUBLE PRECISION,

    -- Content
    summary TEXT NOT NULL,
    details JSONB,
    recommendation TEXT,

    -- Context
    window_id INTEGER,
    window_ids JSONB,
    anomaly_result_id INTEGER,

    -- Traffic Context (denormalized for quick access)
    packet_count INTEGER,
    total_bytes BIGINT,
    unique_src_ips INTEGER,
    unique_dst_ips INTEGER,
    packets_per_sec DOUBLE PRECISION,
    bytes_per_sec DOUBLE PRECISION,

    -- Classification
    tags JSONB,
    category VARCHAR(100), -- network_scan, dos_attack, data_exfiltration

    -- Status and Tracking
    status VARCHAR(50) DEFAULT 'new', -- new, acknowledged, investigating, resolved, false_positive
    assigned_to VARCHAR(100),
    acknowledged_at TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_notes TEXT,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    priority INTEGER DEFAULT 0,

    FOREIGN KEY (session_id) REFERENCES pcap_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY (anomaly_result_id) REFERENCES anomaly_results(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_insight_session ON insights(session_id);
CREATE INDEX IF NOT EXISTS idx_insight_status ON insights(status) WHERE status NOT IN ('resolved', 'false_positive');
CREATE INDEX IF NOT EXISTS idx_insight_severity_priority ON insights(severity, priority DESC) WHERE status = 'new';