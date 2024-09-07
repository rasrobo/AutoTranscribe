# Transcription Automation Script

This script automates the transcription of audio and video files using Whisper, converting files to MP3 format if necessary before transcription. It includes mechanisms to handle multiple instances and interruptions gracefully.

## Features

- **Automatic Conversion**: Converts video files to MP3 format before transcription.
- **Locking Mechanism**: Ensures only one instance processes a file at a time.
- **Signal Handling**: Cleans up lock files on script exit, including interruptions.
- **Output Management**: Saves transcription files in the same directory as the input files.

## Prerequisites

- **FFmpeg**: Ensure FFmpeg is installed for audio conversion.
- **Whisper**: Install Whisper for transcription.

## Setup

1. **Clone the Repository**: Clone this repository to your local machine.
2. **Install Dependencies**: Ensure FFmpeg and Whisper are installed and accessible from the command line.

## Usage

1. **Run the Script**: Execute the script from the terminal:
   ```bash
   ./AT.sh
   ```

2. **Monitor Directory**: The script monitors the specified directory (`/mnt/e/AV/Capture`) for new files and processes them in order of modification time, starting with the newest.

3. **Interruptions**: Use `Ctrl-C` to stop the script. The script will clean up lock files to prevent processing issues on subsequent runs.

## Locking Mechanism

- **Lock Files**: The script creates a lock directory for each file being processed. This prevents multiple instances from processing the same file.
- **Verification**: The script checks for the existence of a lock directory before skipping a file.

## Troubleshooting

- **Hanging Issues**: If the script hangs, check system resources and ensure Whisper and FFmpeg are functioning correctly.
- **Lock File Cleanup**: If the script is interrupted, lock files are automatically cleaned up to prevent stale locks.

## Logging

- **Log File**: The script logs its activity to `~/scripts/AT.log`. Check this file for detailed processing information.

## Contribution

Feel free to contribute by submitting issues or pull requests. Ensure your code follows the project's style guidelines.

## License

This project is licensed under the MIT License.

