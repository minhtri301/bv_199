import cv2
import os
import glob
from srs.settings import cfg
# ==============================
# LOAD VIDEO FILES
# ==============================
def get_all_videos(cam_name):
    pattern = os.path.join(cfg.RECORD_ROOT, cam_name, "*", "*.mp4")
    files = sorted(glob.glob(pattern))
    return files

# ==============================
# PLAY VIDEO
# ==============================
def play_videos(video_files):
    if not video_files:
        print("No videos found.")
        return

    cv2.namedWindow("Playback", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Playback", cfg.WINDOW_W, cfg.WINDOW_H)

    index = 0
    paused = False

    while index < len(video_files):
        video_path = video_files[index]
        print(f"\nPlaying: {video_path}")

        cap = cv2.VideoCapture(video_path)

        while True:
            if not paused:
                ret, frame = cap.read()
                if not ret:
                    break

                # Hiển thị tên file
                filename = os.path.basename(video_path)
                cv2.putText(
                    frame,
                    filename,
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 255),
                    2,
                )

                cv2.imshow("Playback", frame)

            key = cv2.waitKey(30) & 0xFF

            if key == 27:  # ESC
                cap.release()
                cv2.destroyAllWindows()
                return

            elif key == ord(' '):  # SPACE pause
                paused = not paused

            elif key in (ord('n'), ord('N')):  # next video
                break

        cap.release()
        index += 1

    cv2.destroyAllWindows()

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    CAM_NAME = "cam1"
    videos = get_all_videos(CAM_NAME)
    print(f"Found {len(videos)} videos.")
    play_videos(videos)