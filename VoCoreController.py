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
from KeyboardSwitcher import KeyboardSwitcher
from PIL import ImageFont,Image, ImageDraw
from time import sleep, perf_counter
from vocore_screen import screen

    

#from screen import VocoreScreen
#https://www.fullpace-simracing.com/logicrank.html

#things to add:
# - Qualifying Review ( fuel to use)
# - Classic start screen if no telemetry data is available
# - Remaining session time and laps
# - Revmeter blinks way too early
# - qualify and 00:00 time left show summary of qualifying session (best lap, fuel used, laps completed)


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
DEFAULT_KEYBOARD_DEVICE = "/dev/input/by-id/usb-IDOBAO_ID80_0-event-kbd"


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
        default=None,
        help=(
            "Lock the display to a single widget for the whole run and skip "
            "starting the keyboard listener. If omitted, all widgets are "
            "available and can be cycled through with the keyboard "
            "(Left/Right/Tab to step, 1-9 to jump directly to one)."
        ),
    )
    parser.add_argument(
        "--keyboard-device",
        default=DEFAULT_KEYBOARD_DEVICE,
        help=(
            "Path to the keyboard input device used for widget switching "
            f"(default: {DEFAULT_KEYBOARD_DEVICE}). Ignored when --widget is set."
        ),
    )
    return parser.parse_args()


args = parse_args()

#screen = screen.VocoreScreen()   # initialize the screen
#screen.set_brightness(160)
revMeter = RevMeter()
tireInfo = TireInfo()
fuelInfo = FuelInfo()
deltaInfo = DeltaInfo()
leaderboardInfo = LeaderboardInfo()

# Widgets are cycled through with the keyboard (Left/Right or Tab to step,
# 1-9 to jump straight to one) instead of all being drawn on top of each
# other. Order here is the cycle order and also the 1/2/3/... index.
# Passing --widget on the command line locks to a single widget and skips
# the keyboard listener entirely (no keyboard device access needed).
widgetManager = WidgetManager(WIDGET_NAMES)
keyboardSwitcher = None
if args.widget:
    widgetManager.select(args.widget)
    print(f"Widget locked to '{args.widget}' via --widget; keyboard switching disabled")
else:
    keyboardSwitcher = KeyboardSwitcher(args.keyboard_device)

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

        if keyboardSwitcher is not None:
            for command, value in keyboardSwitcher.drain_commands():
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
            #screen.draw_image(img)
finally:
    if keyboardSwitcher is not None:
        keyboardSwitcher.close()
    telemetryReader.close()  # Close the telemetry data
