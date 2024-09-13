### AutoTranscribe README

#### Overview

AutoTranscribe is a Python script designed to automatically transcribe audio and video files. It leverages FFmpeg for media processing and Whisper for transcription, making it a powerful tool for converting multimedia content into text.

#### Use Case

AutoTranscribe is ideal for users who need to transcribe large volumes of audio or video files efficiently. Here are some key use cases:

- **Content Creators**: Transcribe video or audio recordings for blog posts, social media, or other content.
- **Researchers**: Transcribe interviews, lectures, or other audio/video recordings for research purposes.
- **Accessibility**: Generate transcripts for audio/video content to improve accessibility.

#### How It Works

1. **Directory Monitoring**:
   - The script continuously monitors a specified directory for new audio and video files.
   - Supported file formats include MP4, M4A, and MP3.

2. **File Integrity Check**:
   - Uses FFprobe to check the integrity of each file before processing.
   - Ensures that files are valid and within a specified duration limit.

3. **Repair Attempt**:
   - If a file is corrupted, the script attempts to repair it using FFmpeg.
   - If repair fails, the file is moved to a "corrupt" folder.

4. **Conversion to Audio**:
   - Converts video files to audio format (MP3) using FFmpeg.
   - Ensures consistent audio format for transcription.

5. **Transcription**:
   - Uses Whisper to transcribe the audio files.
   - Supports multiple languages and models.

6. **Repetitive Output Detection**:
   - Checks for repetitive output in the transcription results.
   - Stops transcription if repetitive output is detected.

7. **Lock Management**:
   - Uses lock files to prevent multiple instances from processing the same file simultaneously.
   - Ensures that each file is processed only once.

8. **Logging and Error Handling**:
   - Logs detailed information about the processing steps, including errors and warnings.
   - Provides robust error handling to ensure the script continues running even if some files fail.

9. **Chunk Processing**:
   - For large files, breaks them into smaller chunks for efficient processing.
   - Ensures that chunk files are stored in a temporary directory and cleaned up after processing.

#### Installation and Usage

1. **Prerequisites**:
   - Install Python 3.x
   - Install FFmpeg and Whisper
   - Clone the AutoTranscribe repository

2. **Running the Script**:
   ```bash
   python3 AutoTranscribe.py --monitor_dir /path/to/your/directory
   ```
   Replace `/path/to/your/directory` with the directory containing your audio/video files.

3. **Configuration**:
   - Adjust the `MONITOR_DIR` variable in the script to point to your desired directory.
   - Modify other constants (e.g., `MAX_CONCURRENT_PROCESSES`, `WHISPER_TIMEOUT`) as needed.

#### SEO Keywords

- **Automatic Transcription**
- **Audio Transcription**
- **Video Transcription**
- **FFmpeg**
- **Whisper**
- **Python Script**
- **Media Processing**
- **Content Accessibility**

#### Behind the Scenes

Here's a detailed look at what the script does behind the scenes:

1. **Directory Scanning**:
    ```python
    pending_files = find_pending_files()
    ```
    The script scans the specified directory for new files every minute.

2. **File Integrity Check**:
    ```python
    if not is_valid_media_file(file_path):
        if attempt_repair(file_path):
            logging.info(f"File {file_path} was successfully repaired")
        else:
            logging.error(f"Unable to repair {file_path}")
            return
    ```
    It checks each file's integrity using FFprobe and attempts to repair corrupted files.

3. **Conversion to Audio**:
    ```python
    if file_path.suffix in ('.mp4', '.m4a'):
        audio_file = base_name.with_suffix('.mp3')
        if not convert_to_audio(file_path, audio_file):
            return
        file_path = audio_file
    ```
    Video files are converted to audio format using FFmpeg.

4. **Transcription**:
    ```python
    whisper_cmd = [
        "whisper", str(file_path), "--model", "tiny",
        "--language", LANGUAGE_MODE, "--output_dir", str(output_dir)
    ]
    result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT)
    ```
    The script uses Whisper to transcribe the audio files.

5. **Repetitive Output Detection**:
    ```python
    if check_repetition(result.stdout):
        logging.warning(f"Repetitive output detected for {file_path}. Stopping transcription.")
    ```
    It checks for repetitive output in the transcription results.

6. **Lock Management**:
    ```python
    lock_file = LOCK_DIR / f"{base_name.name}.lock"
    if lock_file.exists():
        logging.info(f"Skipping {file_path} as it is currently being processed by another instance.")
        return
    ```
    The script uses lock files to prevent multiple instances from processing the same file simultaneously.

7. **Chunk Processing**:
    ```python
    def process_large_file(file_path, chunk_duration=CHUNK_DURATION):
        audio = AudioSegment.from_file(file_path)
        total_duration = len(audio) / 1000  # in seconds
        chunks = []
        for i in range(0, int(total_duration), chunk_duration):
            chunk = audio[i*1000:(i+chunk_duration)*1000]
            chunk_file = f"{file_path.stem}_chunk_{i}.mp3"
            chunk.export(chunk_file, format="mp3")
            chunks.append(chunk_file)
        return chunks
    ```
    For large files, the script breaks them into smaller chunks for efficient processing.

8. **Temporary Directory Cleanup**:
    ```python
    temp_dir = Path(os.getenv('TEMP', '/tmp')) / "transcription_chunks"
    temp_dir.mkdir(parents=True, exist_ok=True)
    chunk_files = [temp_dir / f"{file_path.stem}_chunk_{i}.mp3" for i in range(chunks)]
    # Process chunks and clean up
    for chunk_file in chunk_files:
        chunk_file.unlink(missing_ok=True)
    ```
    Chunk files are stored in a temporary directory and cleaned up after processing.

By running this script against a directory of AV files, you can automate the transcription process efficiently, ensuring that all files are processed correctly and any issues are logged and handled appropriately.

