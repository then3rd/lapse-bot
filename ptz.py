import os
import sys
import time

import shutil
import argparse
import requests
from requests.auth import HTTPDigestAuth
import ffmpeg

import secrets


# Visible range
DEFAULT_TILT = 14
HORIZON_RANGE = [-120, 60]
STEPS = 90
# HORIZON_RANGE = [-110, -80]
# STEPS = 6

# INTERVAL = 5
INTERVAL = 20  # seconds
LAG = 5

HOST, USER, PASS =  secrets.HOST, secrets.USER, secrets.PASS
PTZ_URL = f"http://{HOST}/axis-cgi/com/ptz.cgi"
JPG_URL = f"http://{HOST}/jpg/image.jpg"
FRAME_NAME = "frame"
OUTPUT_DIR = "out"
OUTPUT_VIDEO = "output.mp4"
GOOD_RESP = [200, 204]


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

    assert STEPS >= 3
    steps_calc = round((HORIZON_RANGE[1] - HORIZON_RANGE[0]) / STEPS)
    horizon_degrees = list(range(HORIZON_RANGE[0], HORIZON_RANGE[1], steps_calc))
    # TODO: Increase precision
    print(
        f"{len(horizon_degrees)} x {steps_calc}° = {steps_calc *len(horizon_degrees)}°: {horizon_degrees}"
    )

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
        pan = horizon_degrees[index]
        params = make_params(pan=pan)
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

        if args.record:
            try:
                time.sleep(LAG)
                img_resp = requests.get(
                    JPG_URL,
                    auth=HTTPDigestAuth(USER, PASS),
                    stream=True,
                    timeout=INTERVAL,
                )
                if img_resp.status_code in GOOD_RESP:
                    output_file_path = filename(counter, abs(pan))
                    with open(output_file_path, "wb") as output_file:
                        output_file.write(img_resp.content)
                    print(f'Saved frame to "{output_file_path}"')
                    counter += 1
            except Exception as e:
                print(f"Error downloading MJPEG: {e}")

        index += direction
        if index in [len(horizon_degrees), -1]:
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
        print("Interrupted")
        # finalize()
        try:
            sys.exit(130)
        except SystemExit:
            os._exit(130)
