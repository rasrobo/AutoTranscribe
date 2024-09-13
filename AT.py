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
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
import sys
import json
from pydub import AudioSegment

# Set up logging
def setup_logging():
    home = Path.home()
    log_dir = home / "logs" / "AutoTranscribe"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "autotranscribe.log"
    logging.basicConfig(filename=str(log_file), level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

# Define constants
LOCK_DIR = Path(os.getenv('TEMP', '/tmp')) / "transcription_locks"
MONITOR_DIR = Path("/mnt/e/AV/Capture")  # Adjust this path as needed
MAX_RETRIES = 3
REPETITION_THRESHOLD = 0.98
LANGUAGE_MODE = "en"
MAX_CONCURRENT_PROCESSES = 2
WHISPER_TIMEOUT = 14400  # 4 hours timeout for Whisper
MAX_DURATION = 14400  # 4 hours maximum duration for processing
CHUNK_DURATION = 600  # 10 minutes per chunk

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
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logging.error(f"FFprobe failed for {file_path}: {result.stderr}")
            return False
        
        probe_data = json.loads(result.stdout)
        duration = float(probe_data['format']['duration'])
        logging.info(f"File {file_path} duration: {duration} seconds")
        return 0 < duration <= MAX_DURATION
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout checking file integrity: {file_path}")
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Error parsing FFprobe output for {file_path}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error checking file integrity: {file_path} - {str(e)}")
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

def attempt_repair(input_file):
    repaired_file = input_file.with_name(f"{input_file.stem}_repaired{input_file.suffix}")
    
    if repaired_file.exists():
        logging.info(f"Overwriting existing repaired file: {repaired_file}")
        repaired_file.unlink(missing_ok=True)
    
    repair_cmd = [
        "ffmpeg", "-i", str(input_file), "-c", "copy", str(repaired_file)
    ]
    try:
        result = subprocess.run(repair_cmd, capture_output=True, text=True, check=True, timeout=1800)
        logging.info(f"Attempted repair of {input_file}")
        
        if is_valid_media_file(repaired_file):
            repaired_file.replace(input_file)
            logging.info(f"Successfully repaired and replaced {input_file}")
            return True
        else:
            logging.error(f"Repair attempt failed for {input_file}: Repaired file is not valid")
            repaired_file.unlink(missing_ok=True)
            return False
    except subprocess.CalledProcessError as e:
        logging.error(f"Repair attempt failed for {input_file}: {e.stderr}")
        repaired_file.unlink(missing_ok=True)
        return False
    except Exception as e:
        logging.error(f"Unexpected error during repair of {input_file}: {str(e)}")
        repaired_file.unlink(missing_ok=True)
        return False

def process_large_file(file_path, chunk_duration=CHUNK_DURATION):
    temp_dir = Path(os.getenv('TEMP', '/tmp')) / "chunk_files"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    audio = AudioSegment.from_file(str(file_path))
    total_duration = len(audio) / 1000  # in seconds
    chunks = []
    for i in range(0, int(total_duration), chunk_duration):
        chunk = audio[i*1000:(i+chunk_duration)*1000]
        chunk_file = temp_dir / f"{file_path.stem}_chunk_{i}.mp3"
        chunk.export(str(chunk_file), format="mp3")
        chunks.append(chunk_file)
    
    return chunks

def check_repetition(text, threshold=0.9, window_size=100):
    words = text.split()
    if len(words) < window_size * 2:
        return False
    for i in range(len(words) - window_size):
        window1 = ' '.join(words[i:i+window_size])
        window2 = ' '.join(words[i+window_size:i+window_size*2])
        similarity = difflib.SequenceMatcher(None, window1, window2).ratio()
        if similarity > threshold:
            return True
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
            if attempt_repair(file_path):
                logging.info(f"File {file_path} was successfully repaired")
            else:
                move_to_corrupt_folder(file_path)
                logging.error(f"Unable to repair {file_path}")
                return

        if file_path.suffix in ('.mp4', '.m4a'):
            audio_file = base_name.with_suffix('.mp3')
            if not convert_to_audio(file_path, audio_file):
                return
            file_path = audio_file

        if file_path.exists():
            logging.info(f"Transcribing {file_path}")
            
            if file_path.stat().st_size > 100 * 1024 * 1024:  # If file is larger than 100MB
                chunks = process_large_file(file_path)
                transcriptions = []
                for chunk in chunks:
                    chunk_transcription = transcribe_chunk(chunk)
                    transcriptions.append(chunk_transcription)
                    chunk.unlink(missing_ok=True)  # Clean up chunk files
                final_transcription = ' '.join(transcriptions)
            else:
                final_transcription = transcribe_chunk(file_path)

            if check_repetition(final_transcription):
                logging.warning(f"Repetitive output detected for {file_path}. Stopping transcription.")
            else:
                with open(file_path.with_suffix('.txt'), 'w') as f:
                    f.write(final_transcription)
                logging.info(f"Transcription successful for {file_path}")
        else:
            logging.error(f"Error: {file_path} not found after conversion.")

    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
    finally:
        if lock_file.exists():
            shutil.rmtree(lock_file, ignore_errors=True)
            logging.info(f"Lock released for {file_path}")

def transcribe_chunk(chunk_path):
    whisper_cmd = [
        "whisper", str(chunk_path), "--model", "tiny",
        "--language", LANGUAGE_MODE, "--output_dir", str(chunk_path.parent)
    ]
    try:
        result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT)
        if result.returncode == 0:
            return result.stdout
        else:
            logging.error(f"Transcription failed for {chunk_path}: {result.stderr}")
            return ""
    except subprocess.TimeoutExpired:
        logging.error(f"Whisper transcription timed out for {chunk_path}")
        return ""

def move_to_corrupt_folder(file_path):
    corrupt_folder = file_path.parent / "unable_to_repair_corrupt"
    corrupt_folder.mkdir(parents=True, exist_ok=True)
    new_path = corrupt_folder / file_path.name
    file_path.rename(new_path)
    logging.info(f"Moved {file_path} to unable_to_repair_corrupt folder")

def cleanup_stale_locks():
    for lock_file in LOCK_DIR.glob('*.lock'):
        if lock_file.is_dir():
            shutil.rmtree(lock_file, ignore_errors=True)
            logging.info(f"Removed stale lock file: {lock_file}")

def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')
    cleanup_stale_locks()
    sys.exit(0)

def main():
    setup_logging()
    LOCK_DIR.mkdir(parents=True, exist_ok=True)
    cleanup_stale_locks()

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        pending_files = find_pending_files()
        if pending_files:
            display_queue(pending_files)
            with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROCESSES) as executor:
                futures = [executor.submit(process_file, file) for file in pending_files]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(f"Unhandled exception in thread: {str(e)}")
        else:
            logging.info("No pending files. Waiting for new files...")
        
        time.sleep(60)  # Check every minute

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