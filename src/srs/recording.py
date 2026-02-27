import cv2
import subprocess
import time
import os
import threading
import numpy as np
import queue
import json
import logging
import sys
from datetime import datetime
from srs.settings import cfg


# ==============================
# LOGGING SETUP
# ==============================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)


# ==============================
# INIT
# ==============================
os.makedirs(cfg.RECORD_ROOT, exist_ok=True)
logger.info("🚀 srs_forward_video started")


# ==============================
# LOAD ZONES
# ==============================
def load_zones():
    if not os.path.exists(cfg.ZONE_FILE):
        logger.warning("No cam_zone.json found")
        return {}

    with open(cfg.ZONE_FILE, "r") as f:
        raw = json.load(f)

    zones = {cam: np.array(pts, dtype=np.int32) for cam, pts in raw.items()}
    logger.info(f"Zones loaded: {list(zones.keys())}")
    return zones


CAMERA_ZONES = load_zones()


# ==============================
# HELPERS
# ==============================
def scale_polygon(poly, sx, sy):
    return np.array([[int(x * sx), int(y * sy)] for (x, y) in poly], dtype=np.int32)


def bbox_center_inside_polygon(x, y, w, h, poly):
    cx = x + w // 2
    cy = y + h // 2
    return cv2.pointPolygonTest(poly, (cx, cy), False) >= 0


def ffmpeg_cmd(rtsp_url, output_file):
    return [
        "ffmpeg",
        "-rtsp_transport", "tcp",
        "-i", rtsp_url,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-y",
        output_file,
    ]


# ==============================
# CAMERA THREAD
# ==============================
def process_camera(cam_name, rtsp_url, debug_queue=None):

    logger.info(f"[{cam_name}] Starting camera thread")

    cap = cv2.VideoCapture(rtsp_url)
    bg = cv2.createBackgroundSubtractorMOG2(history=1000, varThreshold=50)

    recording = False
    last_motion = 0
    ffmpeg_proc = None

    zone_orig = CAMERA_ZONES.get(cam_name)

    if zone_orig is None:
        logger.warning(f"[{cam_name}] No zone defined → recording disabled")

    while True:
        ret, frame = cap.read()

        if not ret:
            logger.warning(f"[{cam_name}] Cannot read frame, retrying...")
            time.sleep(1)
            continue

        h, w = frame.shape[:2]

        if zone_orig is None:
            continue

        small = cv2.resize(frame, (cfg.MOTION_DETECT_SIZE, cfg.MOTION_DETECT_SIZE))
        sx_small = cfg.MOTION_DETECT_SIZE / float(w)
        sy_small = cfg.MOTION_DETECT_SIZE / float(h)

        zone_small = scale_polygon(zone_orig, sx_small, sy_small)

        mask = bg.apply(small)
        _, mask = cv2.threshold(mask, 250, 255, cv2.THRESH_BINARY)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion = 0
        boxes = []

        for c in contours:
            if cv2.contourArea(c) < cfg.MIN_CONTOUR_AREA:
                continue

            x, y, ww, hh = cv2.boundingRect(c)

            if bbox_center_inside_polygon(x, y, ww, hh, zone_small):
                motion += 1
                boxes.append((x, y, ww, hh))

        now = time.time()

        # ================= RECORD =================
        if motion >= cfg.MIN_MOTION_COUNT:
            last_motion = now

            if not recording:
                date_folder = time.strftime("%Y-%m-%d")
                save_dir = os.path.join(cfg.RECORD_ROOT, cam_name, date_folder)
                os.makedirs(save_dir, exist_ok=True)

                filename = datetime.utcnow().strftime("%Y-%m-%d_%H-%M-%S-%f") + ".mp4"
                out_path = os.path.join(save_dir, filename)

                ffmpeg_proc = subprocess.Popen(
                    ffmpeg_cmd(rtsp_url, out_path),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

                recording = True
                logger.info(f"[{cam_name}] ▶ Start recording: {out_path}")

        elif recording and (now - last_motion > cfg.MOTION_TIMEOUT):
            ffmpeg_proc.terminate()
            recording = False
            logger.info(f"[{cam_name}] ⏹ Stop recording")

        # ================= DEBUG =================
        if debug_queue is not None:
            preview = frame.copy()

            poly_color = (0, 0, 255) if recording else (0, 255, 255)

            overlay = preview.copy()
            cv2.fillPoly(overlay, [zone_orig], poly_color)
            preview = cv2.addWeighted(overlay, 0.2, preview, 0.8, 0)
            cv2.polylines(preview, [zone_orig], True, poly_color, 3)

            sx_up = w / float(cfg.MOTION_DETECT_SIZE)
            sy_up = h / float(cfg.MOTION_DETECT_SIZE)

            for (x, y, ww, hh) in boxes:
                x1 = int(x * sx_up)
                y1 = int(y * sy_up)
                x2 = int((x + ww) * sx_up)
                y2 = int((y + hh) * sy_up)
                cv2.rectangle(preview, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(
                preview,
                f"{cam_name} motion={motion} rec={int(recording)}",
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (255, 255, 255),
                2,
            )

            if debug_queue.full():
                debug_queue.get_nowait()

            debug_queue.put_nowait((cam_name, preview))


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":

    dbg_q = queue.Queue(maxsize=5)

    for cam_name, url in cfg.CAMERAS.items():
        t = threading.Thread(
            target=process_camera,
            args=(cam_name, url, dbg_q if cfg.SHOW_DEBUG else None),
            daemon=True,
        )
        t.start()

    if cfg.SHOW_DEBUG:
        logger.info("Debug UI enabled")
        while True:
            time.sleep(1)
    else:
        logger.info("Running in headless mode")
        while True:
            time.sleep(1)