#!/usr/bin/env python3
"""Pi sender: capture Picamera2 frames and send to signaling server via POST /offer.
Set SIGNALING_SERVER env var (e.g. http://PC_IP:8080) or pass --server.
"""
import asyncio
import os
import sys
import argparse
import json
import datetime

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
        config = self.picam.create_video_configuration(main={"size": (width, height)})
        self.picam.configure(config)
        self.picam.start()

    async def recv(self):
        pts, time_base = await self.next_timestamp()
        loop = asyncio.get_running_loop()
        arr = await loop.run_in_executor(None, self.picam.capture_array)
        # Picamera2 default array is RGB
        frame = av.VideoFrame.from_ndarray(arr, format='rgb24')
        frame.pts = pts
        frame.time_base = time_base
        return frame

async def run(server_url):
    pc = RTCPeerConnection()
    pcs = {pc}

    pc.addTrack(PicameraTrack())

    offer = await pc.createOffer()
    await pc.setLocalDescription(offer)

    # send offer to signaling server
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.post(server_url + '/offer', json={"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}) as resp:
            if resp.status != 200:
                print('Signaling error', resp.status)
                print(await resp.text())
                return
            data = await resp.json()

    await pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type=data['type']))
    print('Connection established; streaming...')

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await pc.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', help='Signaling server URL, e.g. http://192.168.1.10:8080')
    args = parser.parse_args()
    server = args.server or os.environ.get('SIGNALING_SERVER')
    if not server:
        print('Provide --server or set SIGNALING_SERVER env var')
        sys.exit(2)
    asyncio.run(run(server))
