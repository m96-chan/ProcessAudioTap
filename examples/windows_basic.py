from proctap import ProcessAudioCapture
import wave
import argparse
import psutil
import sys
import numpy as np


def find_pid_by_name(process_name: str) -> int:
    """プロセス名からPIDを検出する"""
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'].lower() == process_name.lower():
                return proc.info['pid']
            # .exeなしでも検索できるように
            if proc.info['name'].lower() == f"{process_name.lower()}.exe":
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    raise ValueError(f"Process '{process_name}' not found")


def main():
    parser = argparse.ArgumentParser(
        description="Record audio from a specific process to WAV file"
    )
    parser.add_argument(
        '--pid',
        type=int,
        help="Process ID to capture audio from"
    )
    parser.add_argument(
        '--name',
        type=str,
        help="Process name to capture audio from (e.g., 'VRChat.exe' or 'VRChat')"
    )
    parser.add_argument(
        '--output',
        type=str,
        default="output.wav",
        help="Output WAV file path (default: output.wav)"
    )

    args = parser.parse_args()

    # PIDまたはプロセス名のどちらかが必要
    if args.pid is None and args.name is None:
        parser.error("Either --pid or --name must be specified")

    # プロセス名が指定された場合はPIDを検出
    if args.name:
        try:
            pid = find_pid_by_name(args.name)
            print(f"Found process '{args.name}' with PID: {pid}")
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        pid = args.pid
        print(f"Using PID: {pid}")

    # Audio format configuration
    # WASAPI native format: 48kHz, float32, stereo
    # Output format: 48kHz, 16-bit PCM, stereo
    sample_rate = 48000
    channels = 2

    # WAVファイルの設定
    wav = wave.open(args.output, "wb")
    wav.setnchannels(channels)
    wav.setsampwidth(2)  # 16bit PCM
    wav.setframerate(sample_rate)

    def on_data(pcm, frames):
        # Convert float32 to int16
        # Backend returns float32 data (4 bytes per sample)
        float_samples = np.frombuffer(pcm, dtype=np.float32)
        # Clip to [-1.0, 1.0] and convert to int16
        int16_samples = (np.clip(float_samples, -1.0, 1.0) * 32767).astype(np.int16)
        wav.writeframes(int16_samples.tobytes())

    print(f"Recording audio from PID {pid} to '{args.output}'")
    print(f"Format: {sample_rate}Hz, {channels}ch, 16-bit PCM")
    print("(WASAPI native format: 48kHz float32, converted to 16-bit PCM)")
    print("Press Enter to stop recording...")

    try:
        with ProcessAudioCapture(pid, on_data=on_data):
            input()
    except KeyboardInterrupt:
        print("\nRecording stopped by user")
    finally:
        wav.close()
        print(f"Recording saved to '{args.output}'")


if __name__ == "__main__":
    main()