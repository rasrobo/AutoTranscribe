import os
import subprocess
import time
from pathlib import Path
import logging
import argparse
import platform
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import signal
import sys
import json
import re
import shlex
import difflib
from mutagen import File
from datetime import datetime

# Set up logging
def setup_logging():
    home = Path.home()
    log_dir = home / "logs" / "AutoTranscribe"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "autotranscribe.log"
    logging.basicConfig(filename=str(log_file), level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

# Define constants
MEDIA_EXTENSIONS = ('.mp3', '.wav', '.mp4', '.m4a')
LOCK_DIR = Path(os.getenv('TEMP', '/tmp')) / "transcription_locks"
DEFAULT_MONITOR_DIR = Path("/mnt/e/AV/Capture")  # Adjust this path as needed
PENDING_DIR = DEFAULT_MONITOR_DIR
MAX_RETRIES = 3
LANGUAGE_MODE = "en"
MAX_CONCURRENT_PROCESSES = 2
WHISPER_TIMEOUT = 14400  # 4 hours timeout for Whisper
MAX_DURATION = 14400  # 4 hours maximum duration for processing
TEMP_DIR = Path(os.getenv('TEMP', '/tmp')) / "transcription_chunks"
SKIP_DIR_NAME = "unable_to_repair_corrupt"

def sanitize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_.-]', '_', name)

def escape_path(path: Path) -> str:
    return shlex.quote(str(path))

def rename_file(file_path: Path) -> Path:
    new_filename = sanitize_name(file_path.name)
    new_file_path = file_path.parent / new_filename
    if file_path != new_file_path:
        try:
            new_file_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(new_file_path))
            logging.info(f"Renamed {file_path} to {new_file_path}")
        except Exception as e:
            logging.error(f"Error renaming {file_path}: {str(e)}")
    return new_file_path

def find_pending_files(recursive: bool = False, monitor_dir: Path = None) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    monitor_dir = Path(monitor_dir) if monitor_dir else PENDING_DIR
    files_found = list(monitor_dir.glob(pattern))
    if recursive:
        files_found = [f for f in files_found if SKIP_DIR_NAME not in f.parts]
    pending_files = []
    for f in files_found:
        if f.suffix.lower() in MEDIA_EXTENSIONS:
            txt_exists = f.with_suffix('.txt').exists()
            srt_exists = f.with_suffix('.srt').exists()
            if not (txt_exists or srt_exists):
                pending_files.append(f)
            else:
                logging.info(f"Skipping {f} as transcription file already exists.")
    logging.info(f"Found {len(pending_files)} media files pending transcription.")
    if not pending_files:
        logging.info("No pending files found. Double check the directory and file extensions.")
    else:
        for file in pending_files:
            logging.info(f"Pending file: {file}")
    return pending_files

def display_queue(pending_files: list[Path]) -> None:
    print("Pending files requiring transcription:")
    for file in pending_files:
        print(f" - {file}")
    print(f"Total files pending: {len(pending_files)}")

def is_valid_media_file(file_path: Path) -> bool:
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', escape_path(file_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            logging.error(f"FFprobe failed for {file_path}: {result.stderr}")
            return False
        probe_data = json.loads(result.stdout)
        duration = probe_data.get('format', {}).get('duration', 0)
        if duration is None:
            logging.error(f"FFprobe output for {file_path} does not contain duration")
            return False
        logging.info(f"File {file_path} duration: {duration} seconds")
        return 0 < float(duration) <= MAX_DURATION
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout checking file integrity: {file_path}")
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        logging.error(f"Error parsing FFprobe output for {file_path}: {str(e)}")
    except Exception as e:
        logging.error(f"Unexpected error checking file integrity: {file_path} - {str(e)}")
    return False

def convert_to_audio(input_file: Path, output_file: Path) -> bool:
    ffmpeg_cmd = [
        "ffmpeg", "-nostdin", "-y", "-i", escape_path(input_file), "-vn", "-ar", "44100",
        "-ac", "2", "-b:a", "192k", "-threads", "1", escape_path(output_file)
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

def attempt_repair(input_file: Path) -> bool:
    repaired_file = input_file.with_name(f"{input_file.stem}_repaired{input_file.suffix}")
    if repaired_file.exists():
        logging.info(f"Overwriting existing repaired file: {repaired_file}")
        repaired_file.unlink(missing_ok=True)
    repair_cmd = [
        "ffmpeg", "-i", escape_path(input_file), "-c", "copy", escape_path(repaired_file)
    ]
    try:
        result = subprocess.run(repair_cmd, capture_output=True, text=True, check=True, timeout=1800)
        logging.info(f"Attempted repair of {input_file}")
        if is_valid_media_file(repaired_file):
            shutil.move(str(repaired_file), str(input_file))
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

def check_repetition(text: str, threshold: float = 0.9, window_size: int = 100) -> bool:
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

def process_file(file_path: Path) -> None:
    file_path = rename_file(file_path)  # Ensure the file is renamed
    base_name = file_path.with_suffix('')
    lock_file = LOCK_DIR / f"{base_name.name}.lock"
    output_dir = file_path.parent

    if lock_file.exists():
        logging.info(f"Skipping {file_path} as it is currently being processed by another instance.")
        return

    try:
        LOCK_DIR.mkdir(parents=True, exist_ok=True)  # Ensure LOCK_DIR exists
        lock_file.mkdir(parents=True, exist_ok=False)
        logging.info(f"Lock acquired for {file_path}")

        if not is_valid_media_file(file_path):
            if attempt_repair(file_path):
                logging.info(f"File {file_path} was successfully repaired")
            else:
                logging.error(f"Unable to repair {file_path}")
                return

        if file_path.suffix.lower() in ('.mp4', '.m4a'):
            audio_file = base_name.with_suffix('.mp3')
            if not convert_to_audio(file_path, audio_file):
                return
            file_path = audio_file

        if file_path.exists():
            logging.info(f"Transcribing {file_path}")
            try:
                final_transcription = transcribe_chunk(file_path)
                if check_repetition(final_transcription):
                    logging.warning(f"Repetitive output detected for {file_path}. Stopping transcription.")
                else:
                    # Extract creation date from MP3 metadata
                    creation_date = None
                    try:
                        audio_file = File(file_path)
                        if 'TDRC' in audio_file.tags:
                            creation_date = audio_file.tags['TDRC'].text[0]
                        elif 'TDOR' in audio_file.tags:
                            creation_date = audio_file.tags['TDOR'].text[0]
                    except Exception as e:
                        logging.warning(f"Error extracting creation date from {file_path}: {str(e)}")

                    # Format the creation date if available
                    if creation_date:
                        try:
                            creation_date = datetime.strptime(creation_date, '%Y-%m-%d %H:%M:%S')
                            formatted_date = creation_date.strftime('%Y-%m-%d')
                        except ValueError:
                            logging.warning(f"Invalid creation date format for {file_path}: {creation_date}")
                            formatted_date = None
                    else:
                        formatted_date = None

                    # Write the transcription to a text file
                    with open(file_path.with_suffix('.txt'), 'w') as f:
                        if formatted_date:
                            f.write(f"Creation Date: {formatted_date}\n\n")
                        f.write(final_transcription)
                    logging.info(f"Transcription completed for {file_path}")
            except Exception as e:
                logging.error(f"Error during transcription of {file_path}: {str(e)}")
        else:
            logging.error(f"File {file_path} not found after conversion.")

    finally:
        if lock_file.exists():
            lock_file.rmdir()
            logging.info(f"Lock released for {file_path}")

def transcribe_chunk(file_path: Path) -> str:
    whisper_cmd = [
        "whisper", escape_path(file_path), "--model", "large-v2",
        "--language", LANGUAGE_MODE, "--output_dir", escape_path(file_path.parent)
    ]
    try:
        logging.info(f"Executing Whisper command: {' '.join(whisper_cmd)}")
        result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT)
        if result.returncode == 0:
            logging.info(f"Whisper transcription completed for {file_path}")
            return result.stdout
        else:
            logging.error(f"Whisper transcription failed for {file_path}: {result.stderr}")
            return ""
    except subprocess.TimeoutExpired:
        logging.error(f"Whisper transcription timed out for {file_path}")
        return ""

def signal_handler(sig: int, frame) -> None:
    logging.info("Signal received, stopping...")
    sys.exit(0)

def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="AutoTranscribe Script")
    parser.add_argument('--recursive', action='store_true', help="Recursively process directories")
    parser.add_argument('--monitor_dir', type=str, default=None, help="Directory to monitor")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    monitor_dir = Path(args.monitor_dir) if args.monitor_dir else DEFAULT_MONITOR_DIR
    pending_files = find_pending_files(recursive=args.recursive, monitor_dir=monitor_dir)
    display_queue(pending_files)

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROCESSES) as executor:
        future_to_file = {executor.submit(process_file, file): file for file in pending_files}
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Processing failed for {file}: {str(e)}")

if __name__ == "__main__":
    main()