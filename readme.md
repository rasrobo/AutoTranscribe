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
   - If repair fails, the file is skipped and an error is logged.

4. **Conversion to Audio**:
   - Converts video files to audio format (MP3) using FFmpeg.
   - Ensures consistent audio format for transcription.

5. **Transcription**:
   - Uses Whisper to transcribe the audio files.
   - Supports multiple languages and models.
   - Utilizes the `large-v2` model for highest accuracy in US English transcription.

6. **Repetitive Output Detection**:
   - Checks for repetitive output in the transcription results.
   - Stops transcription if repetitive output is detected.

7. **Lock Management**:
   - Uses lock files to prevent multiple instances from processing the same file simultaneously.
   - Ensures that each file is processed only once.

8. **Multi-Threading**:
   - Utilizes multi-threading to process multiple files concurrently.
   - The number of concurrent processes can be adjusted using the `MAX_CONCURRENT_PROCESSES` constant (default is 4).
   - Improves overall transcription speed by leveraging system resources efficiently.

9. **Metadata Extraction**:
   - Extracts the creation date from the MP3 metadata, if available.
   - Includes the creation date in the generated transcript file.

10. **Logging and Error Handling**:
    - Logs detailed information about the processing steps, including errors and warnings.
    - Provides robust error handling to ensure the script continues running even if some files fail.

#### Installation and Usage

1. **Prerequisites**:
   - Install Python 3.x
   - Install FFmpeg and Whisper
   - Install the required Python dependencies:
     ```
     pip install mutagen
     ```
   - Clone the AutoTranscribe repository

2. **Running the Script**:
   ```bash
   python3 AutoTranscribe.py --monitor_dir /path/to/your/directory [--recursive]
   ```
   - Replace `/path/to/your/directory` with the directory containing your audio/video files.
   - Use the `--recursive` flag to enable recursive scanning of subdirectories.

3. **Configuration**:
   - Adjust the `DEFAULT_MONITOR_DIR` variable in the script to set the default directory to monitor.
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
- **Multi-Threading**
- **Metadata Extraction**

#### Behind the Scenes

Here's a detailed look at what the script does behind the scenes:

1. **Directory Scanning**:
    ```python
    pending_files = find_pending_files(recursive=args.recursive, monitor_dir=monitor_dir)
    ```
    The script scans the specified directory for new files based on the provided `--recursive` flag and `--monitor_dir` argument.

2. **File Integrity Check**:
    ```python
    if not is_valid_media_file(file_path):
        if attempt_repair(file_path):
            logging.info(f"File {file_path} was successfully repaired")
        else:
            logging.error(f"Unable to repair {file_path}")
            return
    ```
    It checks each file's integrity using FFprobe and attempts to repair corrupted files. If repair fails, the file is skipped.

3. **Conversion to Audio**:
    ```python
    if file_path.suffix.lower() in ('.mp4', '.m4a'):
        audio_file = base_name.with_suffix('.mp3')
        if not convert_to_audio(file_path, audio_file):
            return
        file_path = audio_file
    ```
    Video files are converted to audio format using FFmpeg.

4. **Transcription**:
    ```python
    whisper_cmd = [
        "whisper", escape_path(file_path), "--model", "large-v2",
        "--language", LANGUAGE_MODE, "--output_dir", escape_path(file_path.parent)
    ]
    result = subprocess.run(whisper_cmd, capture_output=True, text=True, timeout=WHISPER_TIMEOUT)
    ```
    The script uses Whisper with the `large-v2` model to transcribe the audio files.

5. **Repetitive Output Detection**:
    ```python
    if check_repetition(final_transcription):
        logging.warning(f"Repetitive output detected for {file_path}. Stopping transcription.")
    else:
        with open(file_path.with_suffix('.txt'), 'w') as f:
            if formatted_date:
                f.write(f"Creation Date: {formatted_date}\n\n")
            f.write(final_transcription)
        logging.info(f"Transcription completed for {file_path}")
    ```
    It checks for repetitive output in the transcription results and stops transcription if detected.

6. **Lock Management**:
    ```python
    lock_file = LOCK_DIR / f"{base_name.name}.lock"
    if lock_file.exists():
        logging.info(f"Skipping {file_path} as it is currently being processed by another instance.")
        return
    ```
    The script uses lock files to prevent multiple instances from processing the same file simultaneously.

7. **Multi-Threading**:
    ```python
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_PROCESSES) as executor:
        future_to_file = {executor.submit(process_file, file): file for file in pending_files}
        for future in as_completed(future_to_file):
            file = future_to_file[future]
            try:
                future.result()
            except Exception as e:
                logging.error(f"Processing failed for {file}: {str(e)}")
    ```
    The script utilizes multi-threading with a `ThreadPoolExecutor` to process multiple files concurrently. The number of concurrent processes is determined by the `MAX_CONCURRENT_PROCESSES` constant.

8. **Metadata Extraction**:
    ```python
    try:
        audio_file = File(file_path)
        if 'TDRC' in audio_file.tags:
            creation_date = audio_file.tags['TDRC'].text[0]
        elif 'TDOR' in audio_file.tags:
            creation_date = audio_file.tags['TDOR'].text[0]
    except Exception as e:
        logging.warning(f"Error extracting creation date from {file_path}: {str(e)}")
    ```
    The script attempts to extract the creation date from the MP3 metadata using the `mutagen` library. If the creation date is available, it is included in the generated transcript file.

By running this script against a directory of AV files, you can automate the transcription process efficiently, ensuring that all files are processed correctly and any issues are logged and handled appropriately. The multi-threading functionality allows for faster processing of large volumes of files by leveraging system resources effectively.
