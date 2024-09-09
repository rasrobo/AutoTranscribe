# AutoTranscribe

AutoTranscribe is a Python script that automates the process of converting and transcribing audio and video files. Leveraging the cutting-edge Whisper speech recognition model, it provides highly accurate transcriptions for a wide range of media content. This tool is designed to seamlessly integrate with screen recordings and other captured media, making it effortless to generate precise text transcripts without manual intervention.

## Features

- Automatic detection of new audio and video files in a specified directory
- Conversion of video files to audio format when necessary
- Highly accurate transcription using OpenAI's Whisper model
- Cross-platform compatibility (Windows, macOS, Linux)
- Configurable language settings for transcription
- Robust error handling and logging

## Requirements

- Python 3.6+
- FFmpeg
- OpenAI Whisper

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/rasrobo/AutoTranscribe.git
   ```

2. Install the required Python packages:
   ```
   pip install openai-whisper
   ```

3. Ensure FFmpeg is installed on your system and accessible from the command line.

## Usage

1. Edit the `MONITOR_DIR` variable in the script to point to your desired directory:
   ```python
   MONITOR_DIR = Path("/path/to/your/media/folder")
   ```

2. Run the script:
   ```
   python autotranscribe.py
   ```

3. (Optional) Specify a different monitor directory when running the script:
   ```
   python autotranscribe.py --monitor_dir /path/to/your/media/folder
   ```

## Configuration

You can customize the script by modifying the following variables at the top of the file:

- `LANGUAGE_MODE`: Set to "en" for English or "auto" for automatic language detection.
- `MAX_RETRIES`: Maximum number of transcription attempts per file.
- `REPETITION_THRESHOLD`: Similarity threshold for detecting repetitive output.

## How It Works

1. The script monitors a specified directory for new audio and video files.
2. When a new file is detected, it's converted to a suitable audio format if needed.
3. The audio is then transcribed using the Whisper speech recognition model.
4. Transcripts are saved alongside the original files.

## Automation

To run AutoTranscribe continuously:

1. Use nohup (Linux/macOS):
   ```
   nohup python autotranscribe.py &
   ```

2. Create a scheduled task (Windows) or cron job (Linux/macOS) to run the script periodically.

## Troubleshooting

If you encounter issues:

1. Check the `autotranscribe.log` file for error messages.
2. Ensure you have the latest versions of FFmpeg and Whisper installed.
3. Verify that you have read/write permissions in the monitored directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
