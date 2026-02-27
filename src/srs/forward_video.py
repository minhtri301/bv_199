import time
import os
import threading
import subprocess
import logging
import sys
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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


processing_files = set()
lock = threading.Lock()


# =====================================
# RSYNC UPLOAD (SAFE VERSION)
# =====================================
def rsync_upload(local_path):
    rel_path = os.path.relpath(local_path, cfg.WATCH_DIR)
    remote_dir = os.path.dirname(rel_path)

    mkdir_cmd = [
        "ssh",
        cfg.RSYNC_SSH,
        f"mkdir -p {cfg.REMOTE_BASE}/{remote_dir}"
    ]

    logger.info("EXEC: %s", " ".join(mkdir_cmd))

    subprocess.run(
        mkdir_cmd,
        check=True
    )

    cmd = [
        "rsync",
        "-az",
        rel_path,
        f"{cfg.RSYNC_SSH}:{cfg.REMOTE_BASE}/{remote_dir}/"
    ]

    logger.info("EXEC: %s", " ".join(cmd))

    subprocess.run(
        cmd,
        check=True,
        cwd=cfg.WATCH_DIR
    )


# =====================================
# WATCHDOG HANDLER
# =====================================
class VideoFileHandler(FileSystemEventHandler):

    def on_created(self, event):
        self.handle(event)

    def on_modified(self, event):
        self.handle(event)

    def handle(self, event):
        if event.is_directory:
            return

        if not event.src_path.lower().endswith((".mp4", ".mkv")):
            return

        with lock:
            if event.src_path in processing_files:
                return
            processing_files.add(event.src_path)

        logger.info("[DETECT] %s", event.src_path)

        threading.Thread(
            target=self.wait_until_file_ready,
            args=(event.src_path,),
            daemon=True
        ).start()

    # =====================================
    # WAIT FILE STABLE
    # =====================================
    def wait_until_file_ready(self, path):
        last_size = -1
        stable_count = 0

        while True:
            if not os.path.exists(path):
                logger.warning("File disappeared: %s", path)
                break

            size = os.path.getsize(path)

            if size == last_size:
                stable_count += 1
            else:
                stable_count = 0

            if stable_count >= cfg.STABLE_SECONDS:
                logger.info("[READY] %s", path)
                self.upload_with_retry(path)
                break

            last_size = size
            time.sleep(cfg.CHECK_INTERVAL)

        with lock:
            processing_files.discard(path)

    # =====================================
    # RETRY UPLOAD
    # =====================================
    def upload_with_retry(self, path):
        for attempt in range(1, cfg.RSYNC_RETRY + 1):
            try:
                rsync_upload(path)
                logger.info("Upload OK: %s", path)
                return
            except Exception as e:
                logger.error(
                    "Upload FAIL (%d/%d): %s",
                    attempt,
                    cfg.RSYNC_RETRY,
                    path
                )
                logger.error("Error: %s", str(e))
                time.sleep(3)

        logger.critical("FINAL FAIL: %s", path)


# =====================================
# MAIN
# =====================================
if __name__ == "__main__":

    logger.info("🚀 srs_forward_video started")
    logger.info("Watching folder: %s", cfg.WATCH_DIR)

    observer = Observer()
    observer.schedule(VideoFileHandler(), cfg.WATCH_DIR, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping observer...")
        observer.stop()

    observer.join()