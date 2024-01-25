import sys
import time

from telemetrix import telemetrix

# Run a motor to an absolute position. Server will send a callback notification
# when motion is complete.

# GPIO Pins
# https://osoyoo.com/wp-content/uploads/2017/04/cnc_shield_v3_3.png
# https://www.circuito.io/blog/arduino-uno-pinout/
ENABLE_PIN = 8
Y_PULSE_PIN = 3
Y_DIRECTION_PIN = 6

# flag to keep track of the number of times the callback
# was called. When == 1, exit program
exit_flag = 0


def completion_callback(data):
    global exit_flag
    date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(data[2]))
    print(f"Motor {data[1]} absolute motion completed at: {date}.")
    exit_flag += 1


def running_callback(data):
    if data[1]:
        print("The motor is running.")
    else:
        print("The motor IS NOT running.")


def step_absolute(the_board):
    global exit_flag

    # create an accelstepper instance for a TB6600 motor drive
    # if you are using a micro stepper controller board:
    # pin1 = pulse pin, pin2 = direction
    motor = the_board.set_pin_mode_stepper(
        interface=1, pin1=Y_PULSE_PIN, pin2=Y_DIRECTION_PIN
    )

    # the_board.stepper_is_running(motor, callback=running_callback)
    time.sleep(0.5)

    # set the max speed and acceleration
    the_board.stepper_set_current_position(0, 0)
    the_board.stepper_set_max_speed(motor, 800)
    the_board.stepper_set_acceleration(motor, 800)

    # set the absolute position in steps
    the_board.stepper_move_to(motor, 2000)

    # run the motor
    print("Starting motor...")
    the_board.stepper_run(motor, completion_callback=completion_callback)
    # time.sleep(0.2)
    the_board.stepper_is_running(motor, callback=running_callback)
    # time.sleep(0.2)
    while exit_flag == 0:
        time.sleep(0.2)

    # keep application running
    while exit_flag < 1:
        try:
            time.sleep(0.2)
        except KeyboardInterrupt:
            the_board.shutdown()
            sys.exit(0)
    the_board.shutdown()
    sys.exit(0)


# instantiate telemetrix
board = telemetrix.Telemetrix(com_port="/dev/ttyACM0")
board.set_pin_mode_digital_output(ENABLE_PIN)

try:
    # start the main function
    step_absolute(board)
    board.shutdown()
except KeyboardInterrupt:
    board.shutdown()
    sys.exit(0)
