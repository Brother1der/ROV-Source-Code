# Purpose: Flask REST API wrapping SurfaceBackend for browser access.
# Runs on the Raspberry Pi alongside the LoRa hardware.
# Note: SurfaceBackend imports adafruit_rfm9x and configures GPIO at import time,
# so this server requires the LoRa hardware to be physically connected.
# Run with: python FloatAPI.py
# For production use: gunicorn -w 1 --threads 2 FloatAPI:app

import ast
import threading
import time
from typing import Any

from flask import Flask, jsonify
from flask_cors import CORS
import SurfaceBackend

app = Flask(__name__)
CORS(app)

_lock = threading.Lock()

_state: dict[str, Any] = {
    "status":     "idle",
    "message":    "Awaiting mission start.",
    "start_time": None,
    "data_file":  None,
}


def _set_state(**kwargs: Any) -> None:
    with _lock:
        _state.update(kwargs)


def _run_mission() -> None:
    _set_state(status="connecting", message="Sending start signal to float…", start_time=time.time())

    try:
        ack = SurfaceBackend.start_vertical_profiler()
    except Exception as exc:
        _set_state(status="error", message=f"Radio error during connect: {exc}")
        return

    if not ack:
        _set_state(status="error", message="No ACK received — float did not respond.")
        return

    _set_state(status="running", message="Float acknowledged — mission in progress.")

    def on_first_packet() -> None:
        _set_state(status="receiving", message="Data packets arriving…")

    try:
        filename = SurfaceBackend.receive_float_data(
            filename="received_float_data.txt",
            timeout_duration=30.0,
            on_first_packet=on_first_packet,
        )
    except Exception as exc:
        _set_state(status="error", message=f"Radio error during data receive: {exc}")
        return

    _set_state(status="complete", message="Data transfer complete.", data_file=filename)


@app.route("/api/start", methods=["POST"])
def api_start():
    with _lock:
        current = _state["status"]

    if current not in ("idle", "complete", "error"):
        return jsonify({"error": "Mission already in progress."}), 409

    with _lock:
        _state.update({
            "status":     "idle",
            "message":    "Starting…",
            "start_time": None,
            "data_file":  None,
        })

    thread = threading.Thread(target=_run_mission, daemon=True)
    thread.start()
    return jsonify({"ok": True}), 202


@app.route("/api/status", methods=["GET"])
def api_status():
    with _lock:
        snap = dict(_state)

    elapsed = None
    if snap["start_time"] is not None:
        elapsed = round(time.time() - snap["start_time"])

    return jsonify({
        "state":           snap["status"],
        "message":         snap["message"],
        "elapsed_seconds": elapsed,
    })


@app.route("/api/data", methods=["GET"])
def api_data():
    with _lock:
        status    = _state["status"]
        data_file = _state["data_file"]

    if status != "complete" or data_file is None:
        return jsonify({"error": "No data available yet."}), 404

    try:
        with open(data_file, "rb") as f:
            raw = f.read()
    except OSError as exc:
        return jsonify({"error": f"Cannot read data file: {exc}"}), 500

    try:
        parsed = ast.literal_eval(raw.decode("utf-8"))
        depth_readings: list[tuple[float, float]] = parsed[0]
    except Exception as exc:
        return jsonify({"error": f"Failed to parse data file: {exc}"}), 500

    if not depth_readings:
        return jsonify({"error": "Data file contains no depth readings."}), 500

    t0 = depth_readings[0][0]

    depth_points = [
        {"t": round(ts - t0, 2), "d": round(depth, 4)}
        for ts, depth in depth_readings
    ]

    depths = [p["d"] for p in depth_points]
    max_t  = depth_points[-1]["t"]

    return jsonify({
        "depthPoints": depth_points,
        "stats": {
            "maxDepth": round(max(depths), 4),
            "duration": round(max_t),
            "points":   len(depth_points),
        },
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
