import logging
import queue
import threading

import evdev
from evdev import ecodes

logger = logging.getLogger(__name__)


def resolve_code(text):
    """Resolve a button/axis given as a symbolic evdev name (e.g. 'BTN_TRIGGER',
    'ABS_HAT0X') or a decimal/hex number into its integer evdev code.
    """
    text = str(text).strip()
    name = text.upper()
    if hasattr(ecodes, name):
        value = getattr(ecodes, name)
        if isinstance(value, int):
            return value
    try:
        return int(text, 0)
    except ValueError:
        raise ValueError(
            f"'{text}' is neither a known evdev code name (e.g. BTN_TRIGGER, "
            "ABS_HAT0X) nor a number"
        )


class ControllerSwitcher:
    """Listens for button presses and hat/D-pad moves on a single input
    device - typically a sim racing wheel or gamepad - and queues
    widget-switch commands.

    Unlike a keyboard, controllers have no standardized button layout, so
    both the device path and the button/hat -> action mapping are supplied
    by the caller instead of being guessed. Reads directly from the given
    /dev/input/eventX via evdev on a background thread, so switching works
    even when this script has no window focus (headless). The invoking user
    needs read access to that device node - typically via membership in the
    `input` group (`sudo usermod -aG input $USER`, then re-login/reboot) or
    a udev rule; running as root also works but isn't recommended.

    button_map: {evdev EV_KEY code: (action, value)}
        Fires when that key transitions to pressed.
    hat_map: {(evdev EV_ABS code, target value): (action, value)}
        Fires when that axis reports exactly that value (e.g. a D-pad/hat
        moving to -1 or 1 on ABS_HAT0X/ABS_HAT0Y).

    In both maps, action is "next", "prev", or "select" (with value = the
    widget index to jump to; value is unused for "next"/"prev").
    """

    def __init__(self, device_path, button_map=None, hat_map=None):
        self._commands = queue.Queue()
        self._stop = threading.Event()
        self._button_map = dict(button_map or {})
        self._hat_map = dict(hat_map or {})

        self._device = evdev.InputDevice(device_path)
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()

    def _listen(self):
        try:
            for event in self._device.read_loop():
                if self._stop.is_set():
                    return
                if event.type == ecodes.EV_KEY:
                    # Avoid evdev.categorize(): it looks event.code up in a
                    # fixed name table and raises KeyError for button codes
                    # the kernel headers left unnamed (some wheels send
                    # these) - we only need the raw value, so check it
                    # directly. 1 = pressed, 0 = released, 2 = autorepeat.
                    if event.value != 1:
                        continue
                    self._dispatch(self._button_map.get(event.code))
                elif event.type == ecodes.EV_ABS:
                    self._dispatch(self._hat_map.get((event.code, event.value)))
        except OSError as exc:
            logger.warning("ControllerSwitcher: lost device %s (%s)", self._device.path, exc)
        except Exception:
            logger.exception("ControllerSwitcher: listener crashed for %s", self._device.path)

    def _dispatch(self, mapping):
        if mapping is not None:
            self._commands.put(mapping)

    def drain_commands(self):
        """Return all commands queued since the last call, in order."""
        commands = []
        while True:
            try:
                commands.append(self._commands.get_nowait())
            except queue.Empty:
                break
        return commands

    def close(self):
        self._stop.set()
        try:
            self._device.close()
        except Exception:
            pass
