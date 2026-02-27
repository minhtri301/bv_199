import cv2
import numpy as np
import json
import os
from srs.settings import cfg


# ==============================
# SAVE FUNCTION
# ==============================
def save_zone(cam_name, points):
    if os.path.exists(cfg.ZONE_FILE):
        with open(cfg.ZONE_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}

    data[cam_name] = points

    with open(cfg.ZONE_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Zone saved for {cam_name}")


# ==============================
# DRAW FUNCTION
# ==============================
def setup_zone(cam_name, rtsp_url):
    cap = cv2.VideoCapture(rtsp_url)

    if not cap.isOpened():
        print(f"❌ Cannot open camera {cam_name}")
        return

    points = []
    locked = False

    def mouse_callback(event, x, y, flags, param):
        nonlocal points, locked

        if locked:
            return

        if event == cv2.EVENT_LBUTTONDOWN:
            if len(points) < cfg.MAX_POINTS:
                points.append((x, y))

                # 🔥 Auto lock when full
                if len(points) == cfg.MAX_POINTS:
                    locked = True
                    print("🔒 FULL - Polygon auto locked")

            else:
                print("⚠ Polygon already FULL")

        elif event == cv2.EVENT_RBUTTONDOWN:
            if points:
                points.pop()
                locked = False  # nếu xóa điểm thì unlock lại

    cv2.namedWindow(cam_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(cam_name, cfg.WINDOW_W, cfg.WINDOW_H)
    cv2.setMouseCallback(cam_name, mouse_callback)

    print(f"\n=== SETUP ZONE FOR {cam_name} ===")
    print(f"Left click  : add point (max {cfg.MAX_POINTS})")
    print("Right click : undo")
    print("S           : save")
    print("R           : reset")
    print("ESC         : next camera\n")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        preview = frame.copy()

        # Hiển thị số điểm
        cv2.putText(
            preview,
            f"Points: {len(points)}/{cfg.MAX_POINTS}",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 255),
            2,
        )

        # Nếu FULL thì hiển thị chữ FULL
        if len(points) == cfg.MAX_POINTS:
            cv2.putText(
                preview,
                "FULL",
                (30, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 0, 255),
                3,
            )

        # Vẽ điểm
        for p in points:
            cv2.circle(preview, p, 6, (0, 255, 255), -1)

        # Vẽ line
        for i in range(1, len(points)):
            cv2.line(preview, points[i - 1], points[i], (0, 255, 255), 2)

        # Vẽ polygon khi locked
        if locked and len(points) >= 3:
            poly = np.array(points, dtype=np.int32)
            cv2.polylines(preview, [poly], True, (0, 255, 0), 3)

        cv2.imshow(cam_name, preview)

        key = cv2.waitKey(1) & 0xFF

        if key == 27:  # ESC
            break

        elif key in (ord('r'), ord('R')):
            points = []
            locked = False
            print("🔄 Reset")

        elif key in (ord('s'), ord('S')):
            if len(points) >= 3:
                save_zone(cam_name, points)
            else:
                print("Need at least 3 points to save")

    cap.release()
    cv2.destroyWindow(cam_name)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    for cam_name, url in cfg.CAMERAS.items():
        setup_zone(cam_name, url)

    print("Done.")