#!/usr/bin/env python3

import os
import subprocess
import time
from pathlib import Path
import logging
import argparse
import platform
import difflib
import shutil

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
REPETITION_THRESHOLD = 0.9  # 90% similarity
LANGUAGE_MODE = "en"  # Set to "en" for English or "auto" for automatic language detection

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

        if file_path.suffix in ('.mp4', '.m4a'):
            audio_file = base_name.with_suffix('.mp3')
            logging.info(f"Starting FFmpeg conversion for {file_path}")
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", str(file_path), "-vn", "-ar", "44100",
                "-ac", "2", "-b:a", "192k", "-threads", "2", str(audio_file)
            ]
            result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=1800)
            if result.returncode != 0:
                logging.error(f"FFmpeg conversion failed for {file_path}: {result.stderr}")
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
                result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=3600)
                
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

    except subprocess.TimeoutExpired:
        logging.error(f"Error: Command timed out for {file_path}")
    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
    finally:
        if lock_file.exists():
            shutil.rmtree(lock_file, ignore_errors=True)
            logging.info(f"Lock released for {file_path}")

def main():
    setup_logging()
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    pending_files = find_pending_files()
    display_queue(pending_files)

    for file in pending_files:
        process_file(file)

    print("Setting up watches...")
    while True:
        time.sleep(60)  # Check every minute
        new_files = find_pending_files()
        if new_files:
            print("New files detected:")
            display_queue(new_files)
            for file in new_files:
                process_file(file)

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