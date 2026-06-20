from camera_handler import CameraHandler

def main():
    camera_handler = CameraHandler()
    result = camera_handler.capture_image()
    if result:
        print(f"Image saved at: {result}")
    else:
        print("Failed to capture image.")

if __name__ == "__main__":
    # The main entry point for the script.
    main()
