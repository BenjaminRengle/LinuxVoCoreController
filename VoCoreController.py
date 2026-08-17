import argparse
from widgets.DeltaInfo import DeltaInfo
from widgets.FuelInfo import FuelInfo
from widgets.LeaderboardInfo import LeaderboardInfo
from widgets.RevMeter import RevMeter
from widgets.TireInfo import TireInfo
from widgets.DeltaInfo import DeltaInfo
from RFactor2Data import *
from AssettoCorsaData import ACTelemetryReader
from WidgetManager import WidgetManager
from ControllerSwitcher import ControllerSwitcher, resolve_code
from PIL import ImageFont,Image, ImageDraw
from time import sleep, perf_counter
from vocore_screen import screen

    

#from screen import VocoreScreen
#https://www.fullpace-simracing.com/logicrank.html

#things to add:
# - Qualifying Review ( fuel to use)
# - Classic start screen if no telemetry data is available
# - Remaining session time and laps
# - qualify and 00:00 time left show summary of qualifying session (best lap, fuel used, laps completed)
# - Lap timer currently does not work correctly. Always jumps between +0.0 and -0.0

#Controller switcher bug when turning a specific knob on the wheel:
# ControllerSwitcher: listener crashed for /dev/input/by-id/usb-Cube_Controls_F-CORE_0000-event-joystick
# Traceback (most recent call last):
#   File "/var/home/bazzite/Documents/developement/LinuxVoCoreController/ControllerSwitcher.py", line 70, in _listen
#     key_event = evdev.categorize(event)
#   File "/usr/lib64/python3.14/site-packages/evdev/util.py", line 45, in categorize
#     return event_factory[event.type](event)
#            ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^
#   File "/usr/lib64/python3.14/site-packages/evdev/events.py", line 105, in __init__
#     self.keycode = keys[event.code]


def rotate_image_for_screen(image):
    """Rotate the rendered image 180 degrees for an upside-down screen."""
    return image.transpose(Image.Transpose.ROTATE_180)


def mirror_image_for_screen(image):
    """Flip the rendered image horizontally to correct a mirrored display."""
    return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)


def lap_time_to_seconds(lap):
    """Convert a LapTime struct into total seconds."""
    if not lap:
        return None
    return (
        lap.hours * 3600
        + lap.minutes * 60
        + lap.seconds
        + lap.fraction / 1000.0
    )


def seconds_to_lap_time(total_seconds):
    """Convert an estimated lap time in seconds into a LapTime structure."""
    if total_seconds is None:
        return None

    total_seconds = max(0.0, float(total_seconds))
    whole_seconds = int(total_seconds)
    hours, remainder = divmod(whole_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    fraction = int(round((total_seconds - whole_seconds) * 1000.0))
    fraction = max(0, min(999, fraction))

    return LapTime(
        hours=int(hours),
        minutes=int(minutes),
        seconds=int(seconds),
        fraction=int(fraction),
    )


def drawPositionIndicator(draw, position):
    font_small = ImageFont.truetype("/usr/share/fonts/open-sans/OpenSans-Bold.ttf", 50)
    draw.text((68,350),str(position),anchor="mm",font=font_small,fill="white")



def RevTester(screen):
    img = Image.new("RGB", (800, 480), "Black")
    draw = ImageDraw.Draw(img)

    for rpm in range(1000, 5001, 50):
        img = Image.new("RGB", (800, 480), "Black")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 50, 100, 200), fill=(255, 0, 0) )#red circle on the left side of the evilrank display. Starting at coordinate 0,0 spanning to 100,200 in ABSOLUTE Values.
        draw.rectangle((0, 180, 100, 280), fill=(95,220,40) )#green circle on the left side of the evilrank display

        revMeter.draw(draw, rpm=rpm, gear=2, speed=105, max_rpm=5000)
        drawPositionIndicator(draw, position=3)
        img = mirror_image_for_screen(img)

        screen.draw_image(img)

def TireTester(screen):
    img = Image.new("RGB", (800, 480), "Black")
    draw = ImageDraw.Draw(img)

    for step in range(0, 30):
        pressure = [24.0 + step * 0.05, 24.3 + step * 0.03, 24.1 + step * 0.04, 24.5 + step * 0.02]
        temp = [78 + step, 82 + step, 80 + step, 85 + step]
        wear = [18.0 + step * 0.5, 20.0 + step * 0.3, 16.0 + step * 0.4, 22.0 + step * 0.2]
        slip = [0.05 + step * 0.002, -0.04 + step * 0.001, 0.08 + step * 0.0015, -0.02 + step * 0.001]

        img = Image.new("RGB", (800, 480), "Black")
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, 50, 100, 200), fill=(255, 0, 0) )
        draw.rectangle((0, 180, 100, 280), fill=(95,220,40) )

        tireInfo.draw(draw, pressure, temp, wear, slip)
        drawPositionIndicator(draw, position=3)
        img = mirror_image_for_screen(img)
        
        screen.draw_image(img)


def FuelTester(screen):
    for step in range(0, 30):
        current_fuel = 37.5 - step * 0.5
        fuel_capacity = 147.0
        remaining_laps = max(0.0, 14.9 - step * 0.15)
        remaining_time_seconds = max(0, 1578 - step * 18)
        fuel_to_add = 0.0 if current_fuel > 40 else 2.5
        last_lap_fuel = 2.5 + (step % 3) * 0.1
        avg_per_lap = 2.5

        img = Image.new("RGB", (800, 480), "Black")
        draw = ImageDraw.Draw(img)
        #draw.rectangle((0, 50, 100, 200), fill=(255, 0, 0) )
        #draw.rectangle((0, 180, 100, 280), fill=(95,220,40) )

        fuelInfo.draw(
            draw,
            current_fuel=current_fuel,
            fuel_capacity=fuel_capacity,
            remaining_laps=remaining_laps,
            remaining_time_seconds=remaining_time_seconds,
            fuel_to_add=fuel_to_add,
            last_lap_fuel=last_lap_fuel,
            avg_per_lap=avg_per_lap,
        )
        drawPositionIndicator(draw, position=3)
        img = mirror_image_for_screen(img)

        screen.draw_image(img)


WIDGET_NAMES = ["fuel", "revmeter", "tires", "delta", "leaderboard"]
SIM_NAMES = ["rf2", "ac"]
TARGET_FPS = 30
FRAME_INTERVAL = 1.0 / TARGET_FPS


def parse_action(text):
    """Parse an action spec: 'next', 'prev', or 'select:N' (N = 0-based
    index into WIDGET_NAMES)."""
    if text in ("next", "prev"):
        return (text, None)
    if text.startswith("select:"):
        try:
            index = int(text.split(":", 1)[1])
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid widget index in '{text}'")
        return ("select", index)
    raise argparse.ArgumentTypeError(
        f"invalid action '{text}' (expected 'next', 'prev', or 'select:N')"
    )


def parse_controller_button(text):
    """Parse a --controller-button spec of the form CODE=ACTION."""
    if "=" not in text:
        raise argparse.ArgumentTypeError(
            f"invalid --controller-button '{text}' (expected CODE=ACTION)"
        )
    code_text, action_text = text.split("=", 1)
    try:
        code = resolve_code(code_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))
    return (code, parse_action(action_text))


def parse_controller_hat(text):
    """Parse a --controller-hat spec of the form AXIS:VALUE=ACTION."""
    if "=" not in text or ":" not in text:
        raise argparse.ArgumentTypeError(
            f"invalid --controller-hat '{text}' (expected AXIS:VALUE=ACTION)"
        )
    axis_value_text, action_text = text.split("=", 1)
    axis_text, value_text = axis_value_text.split(":", 1)
    try:
        axis_code = resolve_code(axis_text)
        value = int(value_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc))
    return ((axis_code, value), parse_action(action_text))


def parse_args():
    parser = argparse.ArgumentParser(description="VoCore telemetry display controller")
    parser.add_argument(
        "--sim",
        choices=SIM_NAMES,
        default="rf2",
        help=(
            "Which sim to read telemetry from: 'rf2' for rFactor2/Le Mans "
            "Ultimate shared memory, 'ac' for Assetto Corsa's acpmf_physics/"
            "acpmf_static/acpmf_graphics shared memory (default: rf2)."
        ),
    )
    parser.add_argument(
        "--widget",
        choices=WIDGET_NAMES,
        default=WIDGET_NAMES[0],
        help=(
            "Which widget to display at startup "
            f"(default: {WIDGET_NAMES[0]}). Order: {', '.join(WIDGET_NAMES)}."
        ),
    )
    parser.add_argument(
        "--controller-device",
        default=None,
        help=(
            "Path to a game controller/wheel input device (e.g. something "
            "under /dev/input/by-id/) to use for widget switching. Find "
            "yours and its button/axis codes with `evtest` or "
            "`cat /proc/bus/input/devices`. If omitted, widget switching "
            "stays disabled."
        ),
    )
    parser.add_argument(
        "--controller-button",
        action="append",
        default=[],
        type=parse_controller_button,
        metavar="CODE=ACTION",
        help=(
            "Map a controller button to an action. CODE is an evdev key "
            "code, symbolic (e.g. BTN_TRIGGER) or numeric. ACTION is "
            "'next', 'prev', or 'select:N' (N = 0-based widget index, see "
            "--widget's order). Repeatable. Example: "
            "--controller-button BTN_TRIGGER=next"
        ),
    )
    parser.add_argument(
        "--controller-hat",
        action="append",
        default=[],
        type=parse_controller_hat,
        metavar="AXIS:VALUE=ACTION",
        help=(
            "Map a D-pad/hat direction to an action. AXIS is an evdev abs "
            "code, symbolic (e.g. ABS_HAT0X) or numeric, VALUE is the "
            "value reported for that direction (usually -1 or 1). ACTION "
            "is 'next', 'prev', or 'select:N'. Repeatable. Example: "
            "--controller-hat ABS_HAT0X:1=next"
        ),
    )
    return parser.parse_args()


args = parse_args()

screen = screen.VocoreScreen()   # initialize the screen
screen.set_brightness(160)
revMeter = RevMeter()
tireInfo = TireInfo()
fuelInfo = FuelInfo()
deltaInfo = DeltaInfo()
leaderboardInfo = LeaderboardInfo()

# --widget picks the widget shown at startup; if --controller-device and
# some --controller-button/--controller-hat mappings are given, it can be
# switched at runtime from a game controller (e.g. buttons/D-pad on a sim
# racing wheel). With no --controller-device, the display just stays on the
# --widget one for the whole run.
widgetManager = WidgetManager(WIDGET_NAMES)
widgetManager.select(args.widget)

controllerSwitcher = None
if args.controller_device:
    try:
        controllerSwitcher = ControllerSwitcher(
            args.controller_device,
            button_map=dict(args.controller_button),
            hat_map=dict(args.controller_hat),
        )
    except OSError as exc:
        raise SystemExit(
            f"error: cannot open controller device '{args.controller_device}': {exc}\n"
            "Check the path and that your user has permission (member of "
            "the 'input' group, or a udev rule)."
        )

#TireTester(screen)  # Run the TireTester function to test the tire info display
#RevTester(screen)  # Run the RevTester function to test the rev meter display
#FuelTester(screen)  # Run the FuelTester function to test the fuel info display

telemetryReader = ACTelemetryReader() if args.sim == "ac" else RF2TelemetryReader()
print(f"Reading telemetry from: {args.sim}")

while not telemetryReader.open():  # Open the telemetry data
    sleep(5)  # Wait for 1 second before retrying

try:
    next_frame_time = perf_counter()
    while True:
        # The panel can only refresh at ~30fps, so there's no point burning
        # CPU/USB bandwidth reading telemetry and rendering any faster than
        # that - pace the loop to a steady cadence instead of running flat out.
        now = perf_counter()
        sleep_time = next_frame_time - now
        if sleep_time > 0:
            sleep(sleep_time)
        next_frame_time = max(now, next_frame_time) + FRAME_INTERVAL

        if controllerSwitcher is not None:
            for command, value in controllerSwitcher.drain_commands():
                if command == "next":
                    widgetManager.next()
                elif command == "prev":
                    widgetManager.prev()
                elif command == "select":
                    widgetManager.select(value)
                print(f"Active widget: {widgetManager.current}")

        simData = telemetryReader.read()  # Read the telemetry data

        # update the screen with the telemetry data
        img = Image.new("RGB", (800, 480), "Black")
        draw = ImageDraw.Draw(img)

        if simData.gamephase > GamePhase.BEFORE_SESSION:  # Check if the simulation is in a valid game phase (not in menus or loading)
            print(f"Game Phase: {simData.gamephase}, Session: {simData.session}")

            deltaInfo.record_sample(simData)
            delta = deltaInfo.get_delta(simData)
            estimated_lap_seconds = deltaInfo.get_estimated_lap_seconds(simData)
            estimated_lap = seconds_to_lap_time(estimated_lap_seconds) if estimated_lap_seconds is not None else None
            print(
                f"[delta-debug] spline={simData.playerspline:.4f} "
                f"time_into_lap={deltaInfo._laptime_seconds(simData.currentlap)} "
                f"ref_total={deltaInfo._reference_total_time} "
                f"ref_samples={len(deltaInfo._reference_samples) if deltaInfo._reference_samples else 0} "
                f"delta={delta}"
            )

            last_lap_fuel = fuelInfo.record_last_lap_fuel_usage(simData)
            avg_per_lap = fuelInfo.calc_average_fuel_per_lap()
            remaining_laps = None
            if avg_per_lap is not None:
                remaining_laps = fuelInfo.calc_remaining_laps_from_fuel(simData, avg_per_lap)
            avg_lap_time_seconds = fuelInfo.calc_average_lap_time()
            remaining_time_seconds = None
            if remaining_laps is not None and avg_lap_time_seconds is not None:
                remaining_time_seconds = remaining_laps * avg_lap_time_seconds

            active_widget = widgetManager.current

            if active_widget == "fuel":
                print(f"Remaining Laps: {remaining_laps}, Remaining Time (s): {remaining_time_seconds}, Last Lap Fuel: {last_lap_fuel}, Avg per Lap: {avg_per_lap}")
                fuelInfo.draw(
                    draw,
                    current_fuel=simData.fuel,
                    fuel_capacity=simData.fuelcapacity,
                    remaining_laps=remaining_laps,
                    remaining_time_seconds=remaining_time_seconds,
                    fuel_to_add=None,
                    last_lap_fuel=last_lap_fuel,
                    avg_per_lap=avg_per_lap,
                )
            elif active_widget == "revmeter":
                revMeter.draw(draw, simData.rpms, simData.gear, simData.velocity, simData.maxrpm)
            elif active_widget == "tires":
                tireInfo.draw(
                    draw,
                    [simData.tyrepressure[0], simData.tyrepressure[1], simData.tyrepressure[2], simData.tyrepressure[3]],
                    [simData.tyretemp[0], simData.tyretemp[1], simData.tyretemp[2], simData.tyretemp[3]],
                    [simData.tyrewear[0], simData.tyrewear[1], simData.tyrewear[2], simData.tyrewear[3]],
                    [simData.tyreslipratio[0], simData.tyreslipratio[1], simData.tyreslipratio[2], simData.tyreslipratio[3]],
                )
            elif active_widget == "delta":
                deltaInfo.draw(
                    draw,
                    150,
                    20,
                    delta,
                    lap_time=simData.currentlap,
                    estimated_lap=estimated_lap,
                    last_lap=simData.lastlap,
                    best_lap=simData.bestlap,
                    bar_fraction=simData.playerspline,
                    label=""
                )
            elif active_widget == "leaderboard":
                standings = leaderboardInfo.build_standings(
                    simData.cars, simData.position
                )
                leaderboardInfo.draw(draw, standings)

            #draw the EvilRank specific rectangles on the left side of the display
            draw.rectangle((0, 50, 120, 200), fill=(255, 0, 0) )#red circle on the left side of the evilrank display. Starting at coordinate 0,0 spanning to 100,200 in ABSOLUTE Values.
            draw.rectangle((0, 180, 120, 280), fill=(95,220,40) )#green circle on the left side of the evilrank display

            drawPositionIndicator(draw, simData.position)#currently shows the wrong value for multiclass
            img = mirror_image_for_screen(img)
            #draw image on screen and update the display
            screen.draw_image(img)
finally:
    if controllerSwitcher is not None:
        controllerSwitcher.close()
    telemetryReader.close()  # Close the telemetry data
