# LinuxVoCoreController

A Python controller that reads live telemetry from sim racing titles on Linux (Proton) and renders it as a set of dashboard "widgets" (rev meter, fuel, tires, delta, leaderboard) on a [VoCore Screen v2].
The GUI is currently designed to fit the style of the EvilRank DID 4" Dashboard Screen.

## Features

- **Live telemetry** from shared memory.
- **Five dashboard widgets**, one active at a time (selected via `--widget`):
  - **Rev meter** — RPM band, gear, speed, shift-light style redline warning.
  - **Fuel** — current fuel vs. capacity, estimated remaining laps/time, last lap & average consumption, fuel-to-add.
  - **Tires** — pressure, temperature, wear and slip ratio for all four corners.
  - **Delta** — live time delta against your fastest clean lap this session, plus a projected lap time and a track-position progress bar.
  - **Leaderboard** — standings table windowed around your own position (POS / driver / best lap / gap), mirroring the sims' own overlays.
- **Steady 30 FPS render loop**, paced instead of running flat out, since that's the panel's refresh ceiling.

## Supported sims

| Sim | How telemetry is read |
|---|---|
| rFactor2 / Le Mans Ultimate | The game's own SMMP (shared-memory) plugin, read directly from `/dev/shm/$rFactor2SMMP_*` This requires the rF2SharedMemoryMapPlugin_Wine (https://github.com/schlegp/rF2SharedMemoryMapPlugin_Wine) plugin to be installed and activated
| Assetto Corsa | `acpmf_physics` / `acpmf_static` / `acpmf_graphics` shared memory segments via simshmbridge found here: https://github.com/Spacefreak18/simshmbridge

Select which one to read from with `--sim rf2` (default) or `--sim ac`.

As Spacefreak18 explained in the Repository above, mostly all Simracing titles except for LMU and rFactor2 which feature a Wine mapPlugin require briding of Shared Memory from Wine into Linux user space. Check his repository for further information

## Hardware

Talking to the panel itself is handled by [vocore-screen-py](https://github.com/Orangensaft/vocore-screen-py) (used here via a [patched fork](https://github.com/BenjaminRengle/vocore-screen-py.git) with a numpy-vectorized `draw_image` and some PIL/numpy import fixes) — see [Installation](#installation) for how to get it.

## Installation

1. **Clone this repo and its screen-driver dependency as siblings** (the pinned `requirements.txt` entry is a relative editable install, so the two need to sit next to each other):

   ```sh
   git clone https://github.com/BenjaminRengle/LinuxVoCoreController
   git clone https://github.com/BenjaminRengle/vocore-screen-py
   ```

   Layout:
   ```
   developement/
   ├── LinuxVoCoreController/
   └── vocore-screen-py/
   ```

   If you'd rather not use that layout, edit `requirements.txt` and point the `-e ../vocore-screen-py` line at wherever you checked it out (or swap it for a git URL).

2. **Install Python dependencies** (Python 3.7+):

   ```sh
   cd LinuxVoCoreController
   pip install -r requirements.txt
   ```

   This pulls in Pillow (rendering).

3. **USB device permissions.** The screen is read directly from a device node, so your user needs access to it:
   - **Screen (libusb):** add a udev rule so it's accessible without root — see the [vocore-screen-py README](https://github.com/BenjaminRengle/vocore-screen-py.git).
   
   An example Udev rule could look like this:
   ```
   SUBSYSTEM=="usb", ATTR{idVendor}=="c872", ATTR{idProduct}=="1004", MODE="0666", TAG+="uaccess"
   ```
   placed as /etc/udev/rules.d/73-vocore.rules

5. **Fonts.** Widgets render text with Open Sans (`/usr/share/fonts/open-sans/OpenSans-{Bold,Regular,Light}.ttf`). Install an `open-sans` package from your distro, or adjust the font paths in `widgets/*.py` to match wherever it's installed.


## Usage

The simplest way to run it is through `launch.sh`, which also starts a small helper binary (`acshm`, built from the following repository: https://github.com/Spacefreak18/simshmbridge.git) to pre-size Assetto Corsa's shared-memory segments before the controller attaches to them. Point `SIMSHMBRIDGE_DIR` at wherever you've built it if it's not at `../simshmbridge`. rFactor2/LMU need no such helper — their own SMMP plugin creates its shared memory itself.

The default location for my machine was:
```
SIMSHMBRIDGE_DIR="${SIMSHMBRIDGE_DIR:-/home/bazzite/Documents/developement/simshmbridge}"
```

```sh
./launch.sh rf2          # rFactor2 / Le Mans Ultimate
./launch.sh ac           # Assetto Corsa (starts acshm first)
```

Or run the controller directly:

```sh
python3 VoCoreController.py --sim rf2
```

### Command-line options

| Flag | Default | Description |
|---|---|---|
| `--sim {rf2,ac}` | `rf2` | Which sim to read telemetry from. |
| `--widget {fuel,revmeter,tires,delta,leaderboard}` | `fuel` | Which widget to display for the whole run. |

Extra arguments passed to `launch.sh` are forwarded to `VoCoreController.py`, e.g. `./launch.sh rf2 --widget fuel`.

The controller waits for telemetry to become available (retrying every 5s) and only starts drawing once the sim reports a valid, in-session game phase (i.e. not stuck in menus/loading).

Widget switching at runtime (e.g. via keyboard) has been removed for now — the display is locked to whichever widget is selected via `--widget`.

## Project structure

```
VoCoreController.py    Entry point: CLI args, render loop, widget dispatch
SimData.py              Sim-agnostic telemetry data structures (SimData, CarData, LapTime, ...)
RFactor2Data.py          rFactor2/LMU shared-memory reader → SimData
AssettoCorsaData.py       Assetto Corsa shared-memory reader → SimData
WidgetManager.py          Tracks which widget is currently active
widgets/
├── RevMeter.py           Rev meter / gear / speed
├── FuelInfo.py           Fuel level & consumption estimates
├── TireInfo.py           Tire pressure / temp / wear / slip
├── DeltaInfo.py          Live lap delta & projected lap time
└── LeaderboardInfo.py    Standings table
tests/                   Unit tests
launch.sh                 Convenience launcher (handles AC's shm pre-sizing helper)
```

Each sim reader normalizes its raw shared-memory layout into the common `SimData` dataclass (`SimData.py`), so widgets never deal with sim-specific fields or raw memory structs — new sims can be added by writing a reader that produces a `SimData`.

## Adding a widget

1. Create `widgets/MyWidget.py` with a class exposing a `draw(draw, ...)` method (a `PIL.ImageDraw.Draw` plus whatever fields off `SimData` it needs).
2. Instantiate it in `VoCoreController.py` and add its name to `WIDGET_NAMES`.
3. Add a branch for it in the render loop's `if active_widget == ...` chain.

## Known limitations

- Multiclass position indicator on the leaderboard/position badge doesn't account for class yet.
- No "classic" start screen while waiting for telemetry.
- Remaining session time/laps aren't shown.
- Rev meter's shift warning currently triggers earlier than intended.

## License

GPL-3.0 — see [LICENSE](LICENSE).

Special Thanks to https://github.com/Spacefreak18 who did all the work in his projects on how to read telemetry in the first place
