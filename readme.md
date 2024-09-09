# AutoTranscribe

AutoTranscribe is a bash script that automates the process of converting and transcribing audio and video files. It's designed to work seamlessly with screen recordings and other captured media, making it easy to generate text transcripts without manual intervention.

## Use Case

In today's digital world, capturing screen recordings or recording virtual meetings has become increasingly common. While it's relatively easy to create these recordings, transcribing them often remains a manual, time-consuming task. This is where AutoTranscribe comes in.

### The Problem

- Screen recording software and video conferencing tools make it simple to capture audio and video.
- However, converting these recordings into text format typically requires manual effort.
- Transcription can be tedious and time-consuming, especially for long recordings or when dealing with multiple files.

### The Solution

AutoTranscribe addresses these challenges by:

1. Automatically detecting new recordings in a specified directory.
2. Converting video files to audio format if necessary.
3. Using advanced speech recognition to transcribe the audio into text.
4. Organizing the transcripts alongside the original files.

## How It Works

1. **Monitoring**: The script watches a designated folder for new audio or video files.
2. **Conversion**: When a new file is detected, it's converted to a suitable audio format if needed.
3. **Transcription**: The audio is then transcribed using the Whisper speech recognition model.
4. **Output**: Transcripts are saved in the same location as the original files.

## Automation

AutoTranscribe is designed to run continuously or on a schedule:

- It can be set up as a background service to process files as soon as they appear.
- Alternatively, it can be scheduled to run periodically using cron jobs.

For example, to run the script every 15 minutes, you could add the following to your crontab:

```
*/15 * * * * /path/to/AutoTranscribe.sh
```

This automation ensures that your transcripts are always up-to-date without requiring manual intervention.

## Benefits

- **Time-Saving**: Eliminates the need for manual transcription.
- **Consistency**: Provides a uniform approach to handling all recordings.
- **Accessibility**: Makes content more accessible by providing text versions of audio/video files.
- **Searchability**: Enables easy searching through recorded content by converting speech to text.

By using AutoTranscribe, you can streamline your workflow, save time, and make your recorded content more accessible and useful.

Here's the continuation of the README content, focusing on the implementation details and usage instructions:

## Implementation Details

AutoTranscribe is implemented as a bash script that utilizes several key components:

1. **FFmpeg**: Used for audio extraction and conversion.
2. **Whisper**: An advanced speech recognition model for transcription.
3. **inotifywait**: Monitors the specified directory for new files.

The script performs the following steps:

1. Scans the specified directory for audio and video files.
2. Converts video files to audio format (MP3) if necessary.
3. Transcribes the audio using Whisper.
4. Saves the transcription alongside the original file.

## Usage

To use AutoTranscribe:

1. Ensure you have FFmpeg, Whisper, and inotify-tools installed on your system.

2. Clone this repository:
   ```
   git clone https://github.com/yourusername/AutoTranscribe.git
   ```

3. Make the script executable:
   ```
   chmod +x AutoTranscribe.sh
   ```

4. Edit the script to set your desired `MONITOR_DIR`:
   ```bash
   MONITOR_DIR="/path/to/your/media/folder"
   ```

5. Run the script:
   ```
   ./AutoTranscribe.sh
   ```

To run the script in the background or on a schedule, you can use `nohup` or set up a cron job.

## Configuration

You can customize the script by modifying the following variables:

- `LANGUAGE_MODE`: Set to "en" for English or "auto" for automatic language detection.
- `LOG_FILE`: Location of the log file.
- `LOCK_DIR`: Directory for lock files to prevent concurrent processing.

## Troubleshooting

If you encounter issues:

1. Check the log file for error messages.
2. Ensure you have the latest versions of FFmpeg and Whisper installed.
3. Verify that you have read/write permissions in the monitored directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.

