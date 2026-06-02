# Subtitle Creator

Automatically generate synced subtitles for any video — in English or Hebrew — using AI.

## What it does

Drop in a video file, choose a language, and the app produces a ready-to-use `.srt` subtitle file synced to the audio. No manual timing. No editing required.

- **English subtitles** — transcribes speech from any language directly to English
- **Hebrew subtitles** — transcribes and translates to natural Hebrew, right-to-left formatted

## Requirements

- Windows 10 / 11 (64-bit)
- [FFmpeg](https://ffmpeg.org/download.html) installed and on PATH
- Python 3.10 or newer
- Internet connection (AI processing happens in the cloud)

## Setup

1. Download and extract the release zip
2. Run `scripts\setup.ps1` once to install Python dependencies
3. Launch `SubtitleCreator.exe`

## Usage

1. Drop a video file into the app or use the Browse button
2. Click **English Subtitles** or **Hebrew Subtitles**
3. Wait for processing — progress is shown in real time
4. When done, the `.srt` file is saved next to your video (or to your chosen output folder)

## Settings

- **Theme** — switch between system default, light, and dark mode
- **Save subtitles to** — optionally pick a custom output folder

## Version

v0.0.7 — pre-release
