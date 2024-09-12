import os
import subprocess
import time
from pathlib import Path
import logging
import argparse
import platform
import difflib
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up logging
def setup_logging():
    home = Path.home()
    log_dir = home / "logs" / "AutoTranscribe"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "autotranscribe.log"
    logging.basicConfig(filename=str(log_file), level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

# Define constants
LOCK_DIR = Path(os.getenv('TEMP', '/tmp')) / "transcription_locks"
MONITOR_DIR = Path("/mnt/e/AV/Capture")  # Adjust this path as needed
MAX_RETRIES = 3
REPETITION_THRESHOLD = 0.98  # Increased to reduce false positives
LANGUAGE_MODE = "en"
MAX_CONCURRENT_PROCESSES = 4  # Adjust based on your system's capabilities
WHISPER_TIMEOUT = 7200  # 2 hours timeout for Whisper

def find_pending_files():
    pending_files = []
    for ext in ('*.mp4', '*.m4a', '*.mp3'):
        for file_path in sorted(MONITOR_DIR.glob(ext), reverse=True):
            if not (file_path.with_suffix('.txt').exists() or file_path.with_suffix('.srt').exists()):
                pending_files.append(file_path)
    return pending_files

def display_queue(pending_files):
    print("Pending files requiring transcription:")
    for file in pending_files:
        print(f" - {file}")
    print(f"Total files pending: {len(pending_files)}")

def is_valid_media_file(file_path):
    try:
        result = subprocess.run(['ffprobe', '-v', 'error', '-show_entries',
                                 'format=duration', '-of',
                                 'default=noprint_wrappers=1:nokey=1', str(file_path)],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=30)
        logging.debug(f"FFprobe output for {file_path}: {result.stdout.decode().strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout checking file integrity: {file_path}")
        return False
    except Exception as e:
        logging.error(f"Error checking file integrity: {file_path} - {str(e)}")
        return False

def convert_to_audio(input_file, output_file):
    ffmpeg_cmd = [
        "ffmpeg", "-nostdin", "-y", "-i", str(input_file), "-vn", "-ar", "44100",
        "-ac", "2", "-b:a", "192k", "-threads", "1", str(output_file)
    ]
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True, timeout=3600)
        logging.info(f"Successfully converted {input_file} to audio")
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"FFmpeg conversion failed for {input_file}: {e.stderr}")
    except subprocess.TimeoutExpired:
        logging.error(f"FFmpeg conversion timed out for {input_file}")
    return False

def process_file(file_path):
    base_name = file_path.with_suffix('')
    lock_file = LOCK_DIR / f"{base_name.name}.lock"
    output_dir = file_path.parent

    if lock_file.exists():
        logging.info(f"Skipping {file_path} as it is currently being processed by another instance.")
        return

    try:
        lock_file.mkdir(parents=True, exist_ok=False)
        logging.info(f"Lock acquired for {file_path}")

        if not is_valid_media_file(file_path):
            logging.error(f"Skipping invalid or corrupted file: {file_path}")
            return

        if file_path.suffix in ('.mp4', '.m4a'):
            audio_file = base_name.with_suffix('.mp3')
            if not convert_to_audio(file_path, audio_file):
                return
            file_path = audio_file

        if file_path.exists():
            logging.info(f"Transcribing {file_path}")
            
            previous_output = ""
            for attempt in range(MAX_RETRIES):
                whisper_cmd = [
                    "whisper", str(file_path), "--model", "tiny",
                    "--language", LANGUAGE_MODE, "--output_dir", str(output_dir)
                ]
                try:
                    result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT)
                    logging.debug(f"Whisper stdout:\n{result.stdout}")
                    logging.debug(f"Whisper stderr:\n{result.stderr}")
                except subprocess.TimeoutExpired:
                    logging.error(f"Whisper transcription timed out for {file_path}")
                    continue

                # Check for repetitive output
                if attempt > 0:
                    similarity = difflib.SequenceMatcher(None, previous_output, result.stdout).ratio()
                    if similarity > REPETITION_THRESHOLD:
                        logging.warning(f"Repetitive output detected (similarity: {similarity:.2f}). Stopping transcription.")
                        break
                
                previous_output = result.stdout
                
                if result.returncode == 0:
                    logging.info(f"Transcription successful for {file_path}")
                    break
                else:
                    logging.error(f"Transcription attempt {attempt + 1} failed for {file_path}: {result.stderr}")
            
            if attempt == MAX_RETRIES - 1:
                logging.error(f"All transcription attempts failed for {file_path}")
        else:
            logging.error(f"Error: {file_path} not found after conversion.")

    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
    finally:
        if lock_file.exists():
            shutil.rmtree(lock_file, ignore_errors=True)
            logging.info(f"Lock released for {file_path}")

def cleanup_stale_locks():
    for lock_file in LOCK_DIR.glob('*.lock'):
        if lock_file.is_dir():
            shutil.rmtree(lock_file, ignore_errors=True)
            logging.info(f"Removed stale lock file: {lock_file}")

def main():
    setup_logging()
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_locks()

    while True:
        pending_files = find_pending_files()
        display_queue(pending_files)

        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROCESSES) as executor:
            futures = [executor.submit(process_file, file) for file in pending_files]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Unhandled exception in thread: {str(e)}")

        print("Waiting for new files...")
        time.sleep(300)  # Check every 5 minutes

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AutoTranscribe: Automatically transcribe audio and video files.")
    parser.add_argument("--monitor_dir", type=str, help="Directory to monitor for new files")
    args = parser.parse_args()

    if args.monitor_dir:
        MONITOR_DIR = Path(args.monitor_dir)

    if platform.system() == "Windows":
        # Adjust paths for Windows
        LOCK_DIR = Path(os.environ['TEMP']) / "transcription_locks"
        if str(MONITOR_DIR).startswith("/mnt/"):
            MONITOR_DIR = Path(str(MONITOR_DIR).replace("/mnt/", "", 1).replace("/", "\\"))

    main()
