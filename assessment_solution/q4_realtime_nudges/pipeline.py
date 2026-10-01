"""
pipeline.py — Q4 Real-Time Nudges
Core async pipeline:
1. Connects to Deepgram Live for streaming ASR
2. Accumulates transcripts (speaker diarized)
3. Every N seconds, sends chunk to SignalExtractor
4. Passes signals to NudgeEngine
5. Broadcasts resulting nudges to connected clients via WebSockets
"""

import sys
import asyncio
import json
import time
from pathlib import Path
import websockets
from websockets.server import WebSocketServerProtocol

from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DEEPGRAM_API_KEY, CHUNK_DURATION_SECONDS
from q4_realtime_nudges.signal_extractor import extract_signals
from q4_realtime_nudges.nudge_engine import NudgeEngine

# Globals for state
connected_clients: set[WebSocketServerProtocol] = set()
transcript_buffer: list[str] = []
nudge_engine = NudgeEngine()

# Performance Tracking
latency_metrics = {
    "total_chunks_processed": 0,
    "asr_buffer_to_llm_times": [],
    "llm_eval_times": []
}

async def nudge_publisher(websocket: WebSocketServerProtocol, path: str):
    """Handle new websocket connections from the Streamlit Dashboard."""
    connected_clients.add(websocket)
    print(f"[WS] Client connected. Total: {len(connected_clients)}")
    
    # Send history on connect
    if nudge_engine.active_nudges:
        await websocket.send(json.dumps({
            "type": "history",
            "nudges": nudge_engine.active_nudges
        }))
        
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"[WS] Client disconnected.")


async def broadcast_nudge(nudge: dict):
    if not connected_clients:
        return
    msg = json.dumps({"type": "nudge", "nudge": nudge})
    for ws in connected_clients:
        try:
            await ws.send(msg)
        except Exception:
            pass


async def evaluation_loop():
    """Periodically takes the transcript buffer, sends to LLM, and broadcasts nudges."""
    print(f"[Pipeline] Evaluation loop started (Chunk size: {CHUNK_DURATION_SECONDS}s)")
    while True:
        await asyncio.sleep(CHUNK_DURATION_SECONDS)
        
        if not transcript_buffer:
            continue
            
        # 1. Grab buffer and clear it
        chunk_text = "\n".join(transcript_buffer)
        transcript_buffer.clear()
        
        # 2. Extract Signals
        t0 = time.time()
        print(f"[Pipeline] Evaluating chunk ({len(chunk_text)} chars)...")
        match = await extract_signals(chunk_text)
        t_llm = time.time() - t0
        
        latency_metrics["total_chunks_processed"] += 1
        latency_metrics["llm_eval_times"].append(t_llm)
        
        # 3. Process through Nudge rules
        if match:
            nudge = nudge_engine.process_signal(match)
            if nudge:
                print(f"[Pipeline] 🚨 NUDGE GENERATED: {nudge['type']} - {nudge['message']}")
                await broadcast_nudge(nudge)


async def start_deepgram_client():
    """Connect to Deepgram and start receiving streaming audio."""
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)
    dg_connection = deepgram.listen.asyncwebsocket.v("1")
    
    async def on_message(self, result, **kwargs):
        sentence = result.channel.alternatives[0].transcript
        if not sentence:
            return
            
        # Basic diarization logic based on channel/speaker if provided
        # By default, we just append the text
        transcript_buffer.append(f"Speaker: {sentence}")
        print(f"[ASR] {sentence}")
        
        # Send raw realtime transcript to dashboard too
        msg = json.dumps({"type": "transcript", "text": sentence})
        for ws in connected_clients:
            try:
                await ws.send(msg)
            except: pass

    async def on_error(self, error, **kwargs):
        print(f"[ASR Error] {error}")

    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    dg_connection.on(LiveTranscriptionEvents.Error, on_error)

    options = LiveOptions(
        model="nova-2",
        language="en",
        smart_format=True,
        diarize=True,  # Enable speaker separation
        interim_results=False
    )
    
    if await dg_connection.start(options) is False:
        print("[Pipeline] Failed to connect to Deepgram")
        return None
        
    print("[Pipeline] Deepgram connected successfully. Ready for audio.")
    return dg_connection


async def main():
    print("=========================================")
    print("  Q4 Real-Time Nudge Pipeline Starting")
    print("=========================================")

    # 1. Start Websocket Server
    ws_server = await websockets.serve(nudge_publisher, "localhost", 8003)
    print("[Pipeline] Websocket server listening on ws://localhost:8003")

    # 2. Start Deepgram Connection (Waiting for audio input)
    # Normally we'd pass audio from a mic, but we'll expose a TCP socket 
    # so `simulate_call.py` can pipe audio data into us.
    dg_conn = await start_deepgram_client()
    
    # 3. Start LLM Evaluation Loop
    eval_task = asyncio.create_task(evaluation_loop())
    
    # 4. TCP Server to receive audio data chunks from simulation script
    async def audio_receiver(reader, writer):
        print("[Pipeline] Receiver attached. Audio streaming started.")
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                await dg_conn.send(data)
        except Exception as e:
            print(f"[Pipeline] Audio stream error: {e}")
        finally:
            print("[Pipeline] Audio stream ended.")
            writer.close()

    server = await asyncio.start_server(audio_receiver, '127.0.0.1', 8004)
    print("[Pipeline] Audio receiver listening on localhost:8004")
    print("[Pipeline] WAITING FOR SIMULATION (Run `python simulate_call.py`)")
    
    await asyncio.gather(
        ws_server.wait_closed(),
        server.serve_forever(),
        eval_task
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Pipeline] Shutting down...")
        print(f"Metrics: Analyzed {latency_metrics['total_chunks_processed']} chunks. "
              f"Average LLM time: {sum(latency_metrics['llm_eval_times']) / max(1, len(latency_metrics['llm_eval_times'])):.2f}s")
