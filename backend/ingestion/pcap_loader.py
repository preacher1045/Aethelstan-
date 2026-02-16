from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from backend.config import MAX_UPLOAD_SIZE_MB, PROCESSED_DIR, RUST_BINARY, UPLOAD_DIR

# Add scripts directory to path for importing conversion utility
_scripts_dir = Path(__file__).parent.parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
	sys.path.insert(0, str(_scripts_dir))

from convert_pcapng_to_pcap import convert_pcapng_to_pcap as _convert_pcapng


def _resolve_rust_binary() -> Path:
	binary = RUST_BINARY
	if platform.system().lower().startswith("win") and binary.suffix.lower() != ".exe":
		candidate = binary.with_suffix(".exe")
		if candidate.exists():
			binary = candidate
	return binary


def save_upload_file(upload_file: UploadFile, session_id: str) -> Path:
	suffix = Path(upload_file.filename).suffix or ".pcap"
	destination = UPLOAD_DIR / f"{session_id}{suffix}"
	max_bytes = MAX_UPLOAD_SIZE_MB * 1024 * 1024
	bytes_written = 0
	chunk_size = 8 * 1024 * 1024
	with destination.open("wb") as buffer:
		while True:
			chunk = upload_file.file.read(chunk_size)
			if not chunk:
				break
			buffer.write(chunk)
			bytes_written += len(chunk)
			if bytes_written > max_bytes:
				buffer.close()
				destination.unlink(missing_ok=True)
				raise ValueError(f"Upload exceeds max size ({MAX_UPLOAD_SIZE_MB} MB).")
	return destination


def run_rust_extractor(pcap_path: Path, session_id: str) -> Path:
	binary = _resolve_rust_binary()
	if not binary.exists():
		raise FileNotFoundError(
			f"Rust extractor not found at {binary}. Build with `cargo build --release` in backend/features/rust_extractor."
		)

	output_json = PROCESSED_DIR / f"{session_id}_features.json"
	output_json.parent.mkdir(parents=True, exist_ok=True)
	cmd = [str(binary), str(pcap_path), str(output_json)]
	result = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
	if result.returncode != 0:
		raise RuntimeError(f"Extractor failed: {result.stderr.strip()}")
	return output_json


def extract_features_from_path(pcap_path: Path, session_id: str) -> Tuple[Path, Path]:
	pcap_for_extraction = pcap_path
	if pcap_path.suffix.lower() == ".pcapng":
		pcap_converted = pcap_path.with_suffix(".pcap")
		_convert_pcapng(pcap_path, pcap_converted)
		pcap_for_extraction = pcap_converted
	features_json = run_rust_extractor(pcap_for_extraction, session_id)
	return pcap_path, features_json


def extract_features_from_upload(upload_file: UploadFile, session_id: str) -> Tuple[Path, Path]:
	pcap_path = save_upload_file(upload_file, session_id)
	return extract_features_from_path(pcap_path, session_id)
