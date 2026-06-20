import time
from datetime import datetime
import sys

img_dir = './img/'

try:
    from picamera2 import Picamera2
    
except ImportError:
    Picamera2 = None

class CameraHandler:
    def __init__(self):
        if Picamera2 is None:
            print("Warning: 'picamera2' module not found.")
            print("On some systems, you may need to install it via your package manager (e.g., sudo apt-get install python3-picamera2).")

    def capture_image(self):
        """
        Captures a single frame from the camera and saves it as a .jpg file with a timestamp.
        """
        if Picamera2 is None:
            print("Error: 'picamera2' module not found.")
            return None

        try:
            print("Initializing camera hardware...")
            with Picamera2() as camera:
                config = camera.create_still_configuration()
                camera.configure(config)

                camera.start()

                print("Camera initialized successfully. Waiting for stabilization...")
                # Give the camera more time to stabilize after initialization (common requirement on Pi Zero 2W)
                time.sleep(3)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = img_dir + f"capture_{timestamp}.jpg"
                
                print(f"Preparing to capture image: {filename}")
                camera.capture_file(filename)
                print(f"Successfully captured image: {filename}")
                return filename
        except Exception as e:
            print(f"Error during camera operations: {e}")
            return None