# Rust Feature Extractor

A high-performance network feature extraction tool written in Rust for analyzing PCAP files.

## Setup

### Prerequisites
- Rust 1.70+ (install from https://rustup.rs/)
- Windows, macOS, or Linux

### Installation

1. Ensure Rust is installed:
```bash
rustc --version
cargo --version
```

2. If not installed, download from https://rustup.rs/ and run the installer.

## Building

Navigate to this directory and build the project:

```bash
cargo build --release
```

This creates an optimized binary in `target/release/`.

## Running

```bash
cargo run --release
```

## Testing

Run tests with:
```bash
cargo test
```

## Project Structure

- `src/main.rs` - Main application and feature extraction logic
- `Cargo.toml` - Project dependencies and configuration

## Dependencies

- **pcap** (1.1) - PCAP file reading
- **serde** & **serde_json** - JSON serialization/deserialization
- **thiserror** - Error handling
- **log** - Logging

## Features

- Extract network features from PCAP files
- Output in JSON Lines format (.jsonl)
- High-performance processing with release optimizations

## Next Steps

1. Implement PCAP reading logic in `extract_from_pcap()`
2. Parse packet headers for source/destination IPs and ports
3. Calculate network statistics and behavioral features
4. Integrate with Python backend via FFI or subprocess calls

## Debugging

Enable logging by setting `RUST_LOG=debug`:
```bash
RUST_LOG=debug cargo run --release
```

## Integration with Python

You can call the compiled binary from your Python backend:
```python
import subprocess
result = subprocess.run(['./target/release/rust_extractor'], capture_output=True)
```

Or use PyO3 to create Python bindings for direct integration.
