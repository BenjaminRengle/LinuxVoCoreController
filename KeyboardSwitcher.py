import logging
import queue
import threading

import evdev
from evdev import ecodes

logger = logging.getLogger(__name__)


class KeyboardSwitcher:
    """Listens for keypresses on attached keyboards and queues widget-switch commands.

    Reads directly from /dev/input/eventX via evdev on background threads, so
    switching works even when this script has no window focus (headless).
    The invoking user needs read access to those device nodes - typically via
    membership in the `input` group (`sudo usermod -aG input $USER`, then
    re-login/reboot) or a udev rule; running as root also works but isn't
    recommended.

    Keys:
        Right / Tab -> next widget
        Left        -> previous widget
        1-9         -> jump straight to widget at that index
    """

    NEXT_KEYS = {ecodes.KEY_RIGHT, ecodes.KEY_TAB}
    PREV_KEYS = {ecodes.KEY_LEFT}
    DIRECT_KEYS = {
        ecodes.KEY_1: 0,
        ecodes.KEY_2: 1,
        ecodes.KEY_3: 2,
        ecodes.KEY_4: 3,
        ecodes.KEY_5: 4,
        ecodes.KEY_6: 5,
        ecodes.KEY_7: 6,
        ecodes.KEY_8: 7,
        ecodes.KEY_9: 8,
    }

    def __init__(self, device_paths=None):
        self._commands = queue.Queue()
        self._stop = threading.Event()
        self._devices = self._resolve_devices(device_paths)
        self._threads = []

        if not self._devices:
            logger.warning("KeyboardSwitcher: no usable keyboard input devices found")

        for device in self._devices:
            thread = threading.Thread(target=self._listen, args=(device,), daemon=True)
            thread.start()
            self._threads.append(thread)

    def _resolve_devices(self, device_paths):
        if device_paths:
            if isinstance(device_paths, str):
                device_paths = [device_paths]
            devices = []
            for path in device_paths:
                try:
                    devices.append(evdev.InputDevice(path))
                except OSError as exc:
                    logger.error("KeyboardSwitcher: cannot open %s: %s", path, exc)
            return devices

        devices = []
        try:
            candidate_paths = evdev.list_devices()
        except OSError as exc:
            logger.error("KeyboardSwitcher: cannot enumerate /dev/input: %s", exc)
            return devices

        for path in candidate_paths:
            try:
                dev = evdev.InputDevice(path)
            except PermissionError:
                logger.warning(
                    "KeyboardSwitcher: no permission for %s - add your user to the "
                    "'input' group (sudo usermod -aG input $USER, then re-login) "
                    "or add a udev rule",
                    path,
                )
                continue
            except OSError as exc:
                logger.warning("KeyboardSwitcher: skipping %s (%s)", path, exc)
                continue

            caps = dev.capabilities().get(ecodes.EV_KEY, [])
            # Only keep devices that look like a real keyboard (has letter
            # keys), to skip mice/joysticks that only report a few buttons.
            if ecodes.KEY_A in caps and ecodes.KEY_SPACE in caps:
                devices.append(dev)
            else:
                dev.close()

        return devices

    def _listen(self, device):
        try:
            for event in device.read_loop():
                if self._stop.is_set():
                    return
                if event.type != ecodes.EV_KEY:
                    continue
                key_event = evdev.categorize(event)
                if key_event.keystate != key_event.key_down:
                    continue
                self._on_keycode(key_event.scancode)
        except OSError as exc:
            logger.warning("KeyboardSwitcher: lost device %s (%s)", device.path, exc)
        except Exception:
            logger.exception("KeyboardSwitcher: listener crashed for %s", device.path)

    def _on_keycode(self, code):
        if code in self.NEXT_KEYS:
            self._commands.put(("next", None))
        elif code in self.PREV_KEYS:
            self._commands.put(("prev", None))
        elif code in self.DIRECT_KEYS:
            self._commands.put(("select", self.DIRECT_KEYS[code]))

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
        for device in self._devices:
            try:
                device.close()
            except Exception:
                pass
