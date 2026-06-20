#!/usr/bin/env python3
"""Pi sender: capture Picamera2 frames and send to signaling server via POST /offer.
Set SIGNALING_SERVER env var (e.g. http://PC_IP:8080) or pass --server.
"""
import asyncio
import os
import sys
import argparse

from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import av

try:
    from picamera2 import Picamera2
except Exception:
    Picamera2 = None

class PicameraTrack(VideoStreamTrack):
    def __init__(self, width=640, height=480):
        super().__init__()
        if Picamera2 is None:
            raise RuntimeError("picamera2 not available")
        self.picam = Picamera2()
        # Use explicit RGB to avoid red/blue channel swaps from platform-specific 4-channel defaults.
        config = self.picam.create_video_configuration(main={"size": (width, height), "format": "RGB888"})
        self.picam.configure(config)
        self.picam.start()

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        loop = asyncio.get_running_loop()
        arr = await loop.run_in_executor(None, self.picam.capture_array)
        frame = av.VideoFrame.from_ndarray(arr, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self):
        try:
            self.picam.stop()
            self.picam.close()
        finally:
            super().stop()


async def run_once(server_url):
    pc = RTCPeerConnection()
    ended = asyncio.Event()
    end_reason = {"value": "stopped"}

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        state = pc.connectionState
        print(f"Connection state: {state}", flush=True)
        if state in {"failed", "disconnected", "closed"}:
            end_reason["value"] = state
            ended.set()

    pc.addTrack(PicameraTrack())

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(
            server_url.rstrip("/") + "/offer",
            json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type},
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Signaling error {resp.status}: {body}")
            data = await resp.json()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=data["sdp"], type=data["type"]))
    print("Connection established; streaming...", flush=True)

    try:
        await ended.wait()
    finally:
        await pc.close()
    return end_reason["value"]


async def run_forever(server_url, retry_delay=3.0):
    while True:
        try:
            reason = await run_once(server_url)
            print(f"Stream ended ({reason}). Reconnecting in {retry_delay:.1f}s...", flush=True)
        except Exception as exc:
            print(f"Streaming attempt failed: {exc}", flush=True)
            print(f"Retrying in {retry_delay:.1f}s...", flush=True)
        await asyncio.sleep(retry_delay)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', help='Signaling server URL, e.g. http://192.168.1.10:8080')
    parser.add_argument('--retry-delay', type=float, default=3.0, help='Seconds between reconnect attempts')
    args = parser.parse_args()
    server = args.server or os.environ.get('SIGNALING_SERVER')
    if not server:
        print('Provide --server or set SIGNALING_SERVER env var', flush=True)
        sys.exit(2)
    asyncio.run(run_forever(server, retry_delay=args.retry_delay))
