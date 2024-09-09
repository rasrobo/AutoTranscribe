#!/bin/bash

# Define language mode (default to English)
LANGUAGE_MODE="en"

# Define log file location
LOG_FILE=~/scripts/AT.log

# Define lock file directory
LOCK_DIR="/tmp/transcription_locks"

# Create log and lock directories if they do not exist
mkdir -p ~/scripts
mkdir -p "$LOCK_DIR"

# Define monitor directory
MONITOR_DIR="/mnt/e/AV/Capture"

# Function to find pending files
find_pending_files() {
    find "$MONITOR_DIR" -type f \( -name "*.mp4" -o -name "*.m4a" -o -name "*.mp3" \) | sort -r | while read -r file_path; do
        base_name="${file_path%.*}"
        if [ ! -f "${base_name}.txt" ] && [ ! -f "${base_name}.srt" ]; then
            echo "$file_path"
        fi
    done
}

# Display pending files
display_queue() {
    echo "Pending files requiring transcription:"
    local count=0
    while IFS= read -r file; do
        echo " - $file"
        ((count++))
    done
    echo "Total files pending: $count"
}

# Function to process a single file
process_file() {
    local file_path="$1"
    local base_name="${file_path%.*}"
    local file_name=$(basename "$file_path")
    local lock_file="$LOCK_DIR/$(basename "$base_name").lock"
    local output_dir=$(dirname "$file_path")

    # Check if file exists
    if [ ! -f "$file_path" ]; then
        echo "$(date): Error: File not found: $file_path" >> "$LOG_FILE"
        return
    fi

    # Check for existing lock before processing
    if [ -d "$lock_file" ]; then
        echo "Skipping $file_path as it is currently being processed by another instance."
        return
    fi

    # Acquire lock
    if mkdir "$lock_file" 2>/dev/null; then
        echo "Lock acquired for $file_path"
        if [[ "$file_path" == *.mp4 || "$file_path" == *.m4a ]]; then
            echo "$(date): Starting FFmpeg conversion for $file_path" >> "$LOG_FILE"
            AUDIO_FILE="${output_dir}/${base_name##*/}.mp3"
            if ! timeout 30m ffmpeg -nostdin -y -i "$file_path" -vn -ar 44100 -ac 2 -b:a 192k -threads 2 "$AUDIO_FILE" 2>> "$LOG_FILE"; then
                echo "$(date): Error: FFmpeg conversion failed for $file_path" >> "$LOG_FILE"
                rmdir "$lock_file"
                return
            fi
            file_path="$AUDIO_FILE"
        fi

        if [ -f "$file_path" ]; then
            echo "$(date): Transcribing $file_path" >> "$LOG_FILE"
            if ! timeout 1h taskset -c 0-3 whisper "$file_path" --model tiny --language $LANGUAGE_MODE --output_dir "$output_dir" 2>> "$LOG_FILE"; then
                echo "$(date): Error: Whisper transcription failed for $file_path" >> "$LOG_FILE"
            fi
        else
            echo "$(date): Error: $file_path not found after conversion." >> "$LOG_FILE"
        fi

        # Release lock
        rmdir "$lock_file"
        echo "Lock released for $file_path"
    else
        echo "Skipping $file_path as it is currently being processed by another instance."
    fi
}

# Function to clean up lock files and terminate processes on exit
cleanup() {
    echo "Cleaning up lock files and terminating processes..."
    rm -rf "$LOCK_DIR"/*
    pkill -f whisper
    echo "Cleanup complete."
}

# Set trap to clean up lock files and terminate processes on script exit
trap cleanup EXIT

# Handle SIGINT (Ctrl-C) to ensure cleanup
trap "echo 'Interrupted. Cleaning up...'; cleanup; exit 1" SIGINT

# Get and display pending files
pending_files=$(find_pending_files)
echo "$pending_files" | display_queue

# Process pending files
echo "$pending_files" | while IFS= read -r file; do
    process_file "$file"
done

echo "Setting up watches..."
inotifywait -m -e close_write --format '%w%f' "$MONITOR_DIR" | while read NEWFILE
do
    echo "$(date): New file detected: $NEWFILE" >> "$LOG_FILE"
    echo "New file detected: $NEWFILE"
    process_file "$NEWFILE"
done