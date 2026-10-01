"""
dashboard.py — Q4 Real-Time Nudges
Streamlit front-end that connects to the Q4 WebSocket output
and displays real-time transcript + live nudges for the agent.
"""

import sys
import json
import asyncio
import streamlit as st
import websockets
from pathlib import Path

st.set_page_config(page_title="Agent Assist Dashboard", layout="wide", page_icon="🎧")

st.title("🎧 Q4 Live Agent Assist Dashboard")
st.markdown("Real-time signal extraction and nudges powered by Deepgram + GPT-4o")

# Initialize session state for storing live data
if "nudges" not in st.session_state:
    st.session_state["nudges"] = []
if "transcript" not in st.session_state:
    st.session_state["transcript"] = []

# Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📝 Live Call Transcript")
    transcript_container = st.empty()

with col2:
    st.subheader("🚨 Intelligent Nudges")
    nudge_container = st.empty()

def update_ui():
    """Redraw the Streamlit containers based on session state."""
    # Transcript
    t_text = "\n\n".join(st.session_state["transcript"][-15:])  # tail
    transcript_container.info(t_text if t_text else "Waiting for audio stream...")

    # Nudges
    with nudge_container.container():
        if not st.session_state["nudges"]:
            st.write("No active nudges. Monitor transcript.")
        else:
            for n in reversed(st.session_state["nudges"]):
                color = "green"
                if n["severity"] == "warning": color = "orange"
                if n["severity"] == "critical": color = "red"
                
                st.markdown(
                    f"<div style='padding:15px; border-left: 5px solid {color}; "
                    f"background:#f9f9f9; color:#333; margin-bottom:10px; border-radius:3px;'>"
                    f"<b>[{n['timestamp']}] {n['type'].replace('_', ' ').upper()}</b><br>"
                    f"<span style='font-size:16px;'>{n['message']}</span><br>"
                    f"<i style='font-size:12px;color:#777;'>Confidence: {n['confidence']:.2f} | Reasoning: {n['reasoning']}</i>"
                    f"</div>",
                    unsafe_allow_html=True
                )

async def ws_loop():
    """Connect to the pipeline.py websocket and wait for emitted nudges/transcripts."""
    uri = "ws://localhost:8003"
    try:
        async with websockets.connect(uri) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                
                if data["type"] == "nudge":
                    st.session_state["nudges"].append(data["nudge"])
                    # Keep latest 5
                    st.session_state["nudges"] = st.session_state["nudges"][-5:]
                
                elif data["type"] == "transcript":
                    st.session_state["transcript"].append(data["text"])
                
                elif data["type"] == "history":
                    st.session_state["nudges"] = data["nudges"]
                
                # Rerun Streamlit to reflect new data
                st.rerun()

    except ConnectionRefusedError:
        st.error("Cannot connect to pipeline. Is `pipeline.py` running?")
        await asyncio.sleep(2)
        st.rerun()

# Run the async loop
if __name__ == "__main__":
    asyncio.run(ws_loop())
