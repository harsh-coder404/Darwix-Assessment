"""
simulate_call.py — Q4 Real-Time Nudges
Simulates a live phone call by reading a .wav file and streaming
it over a TCP socket to the pipeline at real-time speed.
"""

import sys
import time
import socket
import argparse
import wave
from pathlib import Path

def simulate(wav_path: str):
    if not Path(wav_path).exists():
        print(f"Error: Could not find audio file at {wav_path}")
        sys.exit(1)

    print(f"Starting simulation of {wav_path}")

    # Connect to the pipeline TCP server
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('127.0.0.1', 8004))
    except ConnectionRefusedError:
        print("Error: Could not connect to pipeline at 127.0.0.1:8004")
        print("Please ensure `python pipeline.py` is running first.")
        sys.exit(1)

    with wave.open(wav_path, 'rb') as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        
        # Read in small 0.1 second chunks 
        frames_per_buffer = int(sample_rate * 0.1)
        
        while True:
            data = wf.readframes(frames_per_buffer)
            if not data:
                break
                
            try:
                sock.sendall(data)
                # Sleep to mimic real-time audio generation
                time.sleep(0.1)
            except (BrokenPipeError, ConnectionResetError):
                print("\nPipeline disconnected.")
                break

    print("\nSimulation complete. Audio stream closed.")
    sock.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream audio to Q4 Pipeline")
    parser.add_argument("wav_file", help="Path to the .wav file to stream")
    args = parser.parse_args()
    
    simulate(args.wav_file)
