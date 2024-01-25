"""Camera and Stepper motor time-lapse controller"""
import os
import sys
import time

import shutil
import argparse
import requests
from requests.auth import HTTPDigestAuth
import ffmpeg

import constants as const


# Visible range
DEFAULT_TILT = 14  # Vertical tilt angle

# Long sweep
HORIZON_RANGE = [-120, 60]  # Degree range between start and stop position
STEPS = 90  # Number of steps to compute between horizon range
INTERVAL = 20  # seconds between captures
LAG = 5  # Seconds to wait after move before triggering capture

# Short sweep (test)
# HORIZON_RANGE = [-110, -80]
# STEPS = 6
# INTERVAL = 6
# LAG = 3

HOST, USER, PASS = const.HOST, const.USER, const.PASS
PTZ_URL = f"http://{HOST}/axis-cgi/com/ptz.cgi"
JPG_URL = f"http://{HOST}/jpg/image.jpg"
FRAME_NAME = "frame"
OUTPUT_DIR = "out"
OUTPUT_VIDEO = "output.mp4"
GOOD_RESP = [200, 204]


class AxisCamera:
    """AXIS webcam controller"""

    def do_move(self, pan):
        """Pan camera to degree position"""
        try:
            params = self.make_params(pan=pan)
            move_resp = requests.get(
                PTZ_URL,
                params=params,
                auth=HTTPDigestAuth(USER, PASS),
                timeout=INTERVAL,
            )
            if move_resp.status_code in GOOD_RESP:
                print(f"GET Request Successful for {params}")
            else:
                print(f"Error: {move_resp.status_code}")
        except Exception as e:
            print(f"Error moving axis camera: {e}")

    def save_mjpg(self, file_path):
        """Get and Save MJPEG to file_path"""
        try:
            img_resp = requests.get(
                JPG_URL,
                auth=HTTPDigestAuth(USER, PASS),
                stream=True,
                timeout=INTERVAL,
            )
            if img_resp.status_code in GOOD_RESP:
                with open(file_path, "wb") as output_file:
                    output_file.write(img_resp.content)
                print(f'Saved frame to "{file_path}"')
        except Exception as e:
            print(f"Error downloading MJPEG: {e}")

    @staticmethod
    def make_params(pan, tilt=DEFAULT_TILT):
        """https://www.axis.com/vapix-library/subjects/t10175981/section/t10036011/display"""
        return {
            "pan": pan,
            "tilt": tilt,
            "zoom": "1",
            # "iris": "1",
            # "autofocus": "on",
            # "autoiris": "off",
        }


"""
# class StepperControl:
https://mryslab.github.io/telemetrix/stepper/
https://europe1.discourse-cdn.com/arduino/original/4X/3/b/c/3bcea040a219684ab97f9469e831a20a3abca704.png
"""


def filename(index, suffix):
    """Generate filename"""
    long_index = str(index).zfill(6)
    return f"{OUTPUT_DIR}/{FRAME_NAME}_{long_index}_{suffix}.jpg"


def finalize():
    """Write output video"""
    ffmpeg.input(
        f"{OUTPUT_DIR}/{FRAME_NAME}_*.jpg",
        pattern_type="glob",
        framerate=30,
    ).output(
        OUTPUT_VIDEO,
        vcodec="libx264",
        framerate=30,
    ).overwrite_output().run()
    exit()


def parse_args():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser(description="Weather Front Bot")
    parser.add_argument("-o", "--oscillate", action="store_true", default=False)
    parser.add_argument(
        "-r", "--record", help="Save images", action="store_true", default=False
    )
    parser.add_argument(
        "-f", "--finalize", help="Finalize only", action="store_true", default=False
    )
    parser.add_argument(
        "-t", "--test", help="Exit before action", action="store_true", default=False
    )
    args = parser.parse_args()
    return args


def main():
    """Main Routine"""
    args = parse_args()
    cam = AxisCamera()

    # Calculate degree steps
    assert STEPS >= 3
    pan_degree = round((HORIZON_RANGE[1] - HORIZON_RANGE[0]) / STEPS)
    pan_list = list(range(HORIZON_RANGE[0], HORIZON_RANGE[1], pan_degree))
    # TODO: Increase precision
    print(f"{len(pan_list)} x {pan_degree}° = {pan_degree *len(pan_list)}°: {pan_list}")

    if args.test:
        exit()

    if args.finalize:
        finalize()

    if args.record:
        if os.path.exists(OUTPUT_DIR):
            shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR)

    direction = 1
    index = 0
    counter = 0

    while True:
        # Move camera to iteration position
        pan = pan_list[index]
        cam.do_move(pan)

        # Capture and save image
        if args.record:
            time.sleep(LAG)
            file_path = filename(counter, abs(pan))
            cam.save_mjpg(file_path)
            counter += 1

        # increment step for next iteration
        index += direction

        # Flip direction or break if at last element (end or oscillate)
        if index in [len(pan_list), -1]:
            if args.oscillate:
                direction *= -1
                index += 2 * direction
            else:
                break

        if args.record:
            time.sleep(INTERVAL - LAG)
        else:
            time.sleep(INTERVAL)
    finalize()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if input("Do you want to finalize? (y/N): ").lower() == "y":
            finalize()
        else:
            print("Exiting...")
            try:
                sys.exit(130)
            except SystemExit:
                os._exit(130)
