import time
import os
import threading
import subprocess
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from srs.settings import cfg

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

    print("🚀", " ".join(mkdir_cmd))

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

    print("🚀", " ".join(cmd))

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

        print(f"[DETECT] {event.src_path}")

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
                break

            size = os.path.getsize(path)

            if size == last_size:
                stable_count += 1
            else:
                stable_count = 0

            if stable_count >= cfg.STABLE_SECONDS:
                print(f"[READY] {path}")
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
                print(f"✅ Upload OK: {path}")
                return
            except Exception as e:
                print(f"❌ Upload FAIL ({attempt}/{cfg.RSYNC_RETRY}): {path}")
                print(e)
                time.sleep(3)

        print(f"🔥 FINAL FAIL: {path}")


# =====================================
# MAIN
# =====================================
if __name__ == "__main__":
    observer = Observer()
    observer.schedule(VideoFileHandler(), cfg.WATCH_DIR, recursive=True)
    observer.start()

    print("👀 Watching folder:", cfg.WATCH_DIR)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()