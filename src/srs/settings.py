class Settings:
    ZONE_FILE: str = 'cam_zone.json'
    CAMERAS = {
        "cam1": "rtsp://admin:Rsc@13579@192.168.1.100:554/Streaming/Channels/101",
        # "cam2": "rtsp://admin:Rsc@13579@192.168.1.100:554/Streaming/Channels/101",

    }
    RECORD_ROOT = "/home/ai/.srs_data/records"
    WATCH_DIR = RECORD_ROOT
    STABLE_SECONDS = 10
    CHECK_INTERVAL = 1
    RSYNC_SSH = "rs_3090"
    REMOTE_BASE = f"/ssd1/duongpd/data/BV-199-MINI-PC-1"
    MOTION_TIMEOUT = 15
    MIN_MOTION_COUNT = 2
    MOTION_DETECT_SIZE = 320
    MIN_CONTOUR_AREA = 500

    WINDOW_W = 1280
    WINDOW_H = 720
    SHOW_DEBUG = False
    MAX_POINTS = 10

    RSYNC_TIMEOUT = 600
    RSYNC_RETRY = 3

cfg = Settings()