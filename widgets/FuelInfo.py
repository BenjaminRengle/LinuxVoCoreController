import logging
from collections import deque

from PIL import ImageFont

logger = logging.getLogger(__name__)


class FuelInfo:

    def __init__(self, rolling_window=5):
        """
        Args:
            rolling_window: number of most-recent clean laps averaged for
                avg_per_lap / remaining-laps, so the estimate tracks recent
                driving instead of the whole session.
        """
        self.font_large = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            64
        )

        self.font_medium = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            40
        )

        self.font_small = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            28
        )

        self.font_tiny = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Regular.ttf",
            22
        )

        self._last_fuel = None
        self._last_totalLaps = None
        self._lap_fuel_history = deque(maxlen=rolling_window)
        self._lap_time_history = deque(maxlen=rolling_window)
        self._pit_seen_this_lap = False
        self._last_lap_fuel = None

    # A clean lap burning more than this many times the current rolling
    # average is treated as a data glitch (missed sample, session/fuel
    # reset, pit flag that didn't register in time) rather than genuine
    # consumption, and is excluded from the average.
    OUTLIER_RATIO = 2.5

    def calc_remaining_laps_from_fuel(self, sim_data, avg_fuel_per_lap, cap_to_race_distance=True):
        """Return the number of laps the current fuel can support.

        Args:
            sim_data: SimData instance carrying current fuel and optional race state.
            avg_fuel_per_lap: Fuel consumption in liters per lap.
            cap_to_race_distance: When True, cap the result to the race laps remaining.

        Uses sim_data.fuel from the SimData structure.
        """
        if sim_data is None:
            return None

        current_fuel = getattr(sim_data, "fuel", None)
        if current_fuel is None or avg_fuel_per_lap is None or avg_fuel_per_lap <= 0:
            return None

        laps_by_fuel = float(current_fuel) / float(avg_fuel_per_lap)
        laps_by_fuel = max(0.0, laps_by_fuel)

        if cap_to_race_distance and hasattr(sim_data, "numlaps") and hasattr(sim_data, "totalLaps"):
            remaining_race_laps = None
            if hasattr(sim_data, "playertrackpos"):
                progress = sim_data.playertrackpos
                if progress is not None:
                    if progress > 1.0:
                        progress = float(progress) / 65535.0
                    progress = max(0.0, min(1.0, float(progress)))
                    remaining_race_laps = float(sim_data.numlaps) - float(sim_data.totalLaps) - progress
            if remaining_race_laps is None:
                remaining_race_laps = float(sim_data.numlaps) - float(sim_data.totalLaps)
            if remaining_race_laps < 0:
                remaining_race_laps = 0.0
            return min(laps_by_fuel, remaining_race_laps)

        return laps_by_fuel

    def _laptime_to_seconds(self, laptime):
        """Convert a LapTime struct (hours/minutes/seconds/fraction) to seconds."""
        if not laptime:
            return None
        seconds = (
            laptime.hours * 3600
            + laptime.minutes * 60
            + laptime.seconds
            + laptime.fraction / 1000.0
        )
        return seconds if seconds > 0 else None

    def _car_in_pit(self, sim_data):
        """Whether the player's car is currently in the pits/garage."""
        car_data = getattr(sim_data, "playercardata", None)
        if car_data is None:
            return False
        return bool(getattr(car_data, "inpit", False)) or bool(
            getattr(car_data, "ingarage", False)
        )

    def record_last_lap_fuel_usage(self, sim_data):
        """Record fuel used since the previous lap and return last lap fuel usage.

        This is called on every telemetry sample (many times per lap), so the
        fuel/lap baseline must only be advanced when a lap boundary is actually
        crossed - otherwise it would just measure fuel burned in the last
        fraction of a second instead of over the whole lap.

        Out-laps and in-laps (any lap that touched the pits/garage) are
        skipped for avg_per_lap - a refuel or a lap partly driven at pit-lane
        speed makes them poor predictors of normal per-lap consumption. The
        literal last-lap figure still reflects them since it's just reporting
        what actually happened.
        """
        if sim_data is None:
            return self._last_lap_fuel

        current_fuel = getattr(sim_data, "fuel", None)
        current_numLaps = getattr(sim_data, "lap", None)
        if current_fuel is None or current_numLaps is None:
            return self._last_lap_fuel

        current_fuel = float(current_fuel)
        current_numLaps = int(current_numLaps)

        if self._last_fuel is None or self._last_totalLaps is None:
            self._last_fuel = current_fuel
            self._last_totalLaps = current_numLaps
            self._pit_seen_this_lap = self._car_in_pit(sim_data)
            return self._last_lap_fuel

        self._pit_seen_this_lap = self._pit_seen_this_lap or self._car_in_pit(sim_data)

        laps_completed = current_numLaps - self._last_totalLaps
        if laps_completed > 0:
            fuel_used = self._last_fuel - current_fuel
            if fuel_used > 0:
                per_lap_fuel = fuel_used / float(laps_completed)
                self._last_lap_fuel = per_lap_fuel

                is_pit_lap = laps_completed != 1 or self._pit_seen_this_lap

                is_outlier = False
                if not is_pit_lap and self._lap_fuel_history:
                    current_avg = self.calc_average_fuel_per_lap()
                    if current_avg and per_lap_fuel > current_avg * self.OUTLIER_RATIO:
                        is_outlier = True

                is_clean_lap = not is_pit_lap and not is_outlier
                if is_clean_lap:
                    self._lap_fuel_history.append(per_lap_fuel)

                    lap_time = self._laptime_to_seconds(getattr(sim_data, "lastlap", None))
                    if lap_time:
                        self._lap_time_history.append(lap_time)

                    logger.info(
                        "Fuel usage recorded: %.3f L, avg now %.3f L/lap over %d lap(s)",
                        fuel_used,
                        self.calc_average_fuel_per_lap(),
                        len(self._lap_fuel_history),
                    )
                elif is_outlier:
                    logger.warning(
                        "Fuel usage recorded: %.3f L/lap - excluded as a statistical "
                        "outlier (>%.1fx the current %.3f L/lap average)",
                        per_lap_fuel,
                        self.OUTLIER_RATIO,
                        current_avg,
                    )
                else:
                    logger.info(
                        "Fuel usage recorded: %.3f L over %d lap(s) - excluded from "
                        "average (pit lap or multi-lap gap)",
                        fuel_used,
                        laps_completed,
                    )

            # Only rebase at the lap boundary itself, whether or not the lap
            # counted (e.g. skip refuel laps), so the next lap starts fresh.
            self._last_fuel = current_fuel
            self._last_totalLaps = current_numLaps
            self._pit_seen_this_lap = self._car_in_pit(sim_data)

        return self._last_lap_fuel

    def calc_average_fuel_per_lap(self):
        """Return the average fuel consumption over the last N clean laps."""
        if not self._lap_fuel_history:
            return None
        return sum(self._lap_fuel_history) / len(self._lap_fuel_history)

    def calc_average_lap_time(self):
        """Return the average lap time (seconds) over the last N clean laps."""
        if not self._lap_time_history:
            return None
        return sum(self._lap_time_history) / len(self._lap_time_history)

    def _format_time(self, seconds):
        if seconds is None:
            return "--:--"
        seconds = max(0, int(seconds))
        minutes = seconds // 60
        remainder = seconds % 60
        return f"{minutes}:{remainder:02d}"

    def _format_value(self, value, precision=1, suffix=""):
        if value is None:
            return "--"
        return f"{value:.{precision}f}{suffix}"

    def draw(
        self,
        draw,
        current_fuel,
        fuel_capacity,
        remaining_laps,
        remaining_time_seconds,
        fuel_to_add,
        last_lap_fuel,
        avg_per_lap,
    ):
        """Render the fuel strategy display on the VoCore screen."""
        draw.rectangle((0, 0, 750, 420), fill=(0, 0, 0))

        # Top fuel bar and total fuel text
        margin = 160
        bar_top = 40
        bar_height = 34
        bar_width = 620
        bar_left = margin
        bar_right = bar_left + bar_width

        fill_fraction = 0.0
        if fuel_capacity and fuel_capacity > 0:
            fill_fraction = max(0.0, min(current_fuel / fuel_capacity, 1.0))

        draw.rounded_rectangle(
            (bar_left, bar_top, bar_right, bar_top + bar_height),
            radius=20,
            fill=(60, 60, 60),
        )
        draw.rounded_rectangle(
            (bar_left, bar_top, bar_left + int(bar_width * fill_fraction), bar_top + bar_height),
            radius=20,
            fill=(80, 220, 90),
        )

        draw.text(
            (480, bar_top + bar_height / 2),
            f"{current_fuel:.1f} / {fuel_capacity:.0f} L",
            anchor="mm",
            font=self.font_large,
            fill="white",
        )

        # Remaining laps and remaining time cards
        card_top = bar_top + bar_height + 30
        card_height = 130
        left_card = (margin, card_top, 480, card_top + card_height)
        right_card = (520, card_top, 780, card_top + card_height)

        draw.rounded_rectangle(left_card, radius=24, fill=(255, 255, 255))
        draw.rounded_rectangle(right_card, radius=24, fill=(255, 255, 255))

        draw.text(
            (left_card[0] + 20, left_card[1] + 24),
            "REMAINING LAPS",
            anchor="lm",
            font=self.font_small,
            fill="black",
        )
        draw.text(
            (left_card[2] - 100, left_card[3] - 40),
            self._format_value(remaining_laps, precision=1),
            anchor="rm",
            font=self.font_large,
            fill="black",
        )

        draw.text(
            (right_card[0] + 20, right_card[1] + 24),
            "REMAINING TIME",
            anchor="lm",
            font=self.font_small,
            fill="black",
        )
        draw.text(
            (right_card[2] - 50, right_card[3] - 40),
            self._format_time(remaining_time_seconds),
            anchor="rm",
            font=self.font_large,
            fill="black",
        )

        # Bottom row: fuel to add, last lap, avg/lap
        bottom_top = card_top + card_height + 30
        bottom_height = 210
        fuel_card = (margin, bottom_top, 380, bottom_top + bottom_height)
        last_card = (400, bottom_top, 580, bottom_top + bottom_height)
        avg_card = (600, bottom_top, 780, bottom_top + bottom_height)

        draw.rounded_rectangle(fuel_card, radius=28, fill=(40, 180, 40))
        draw.rounded_rectangle(last_card, radius=28, fill=(255, 255, 255))
        draw.rounded_rectangle(avg_card, radius=28, fill=(255, 255, 255))

        fuel_text = "NONE" if fuel_to_add is None or fuel_to_add == 0 else f"{fuel_to_add:.1f} L"

        draw.text(
            (fuel_card[0] + 20, fuel_card[1] + 24),
            "FUEL TO ADD",
            anchor="lm",
            font=self.font_small,
            fill="black",
        )
        draw.text(
            ((fuel_card[0] + fuel_card[2]) / 2, fuel_card[1] + 110),
            fuel_text,
            anchor="mm",
            font=self.font_large,
            fill="black",
        )

        draw.text(
            (last_card[0] + 20, last_card[1] + 24),
            "LAST LAP",
            anchor="lm",
            font=self.font_small,
            fill="black",
        )
        draw.text(
            (last_card[2] - 20, last_card[3] - 100),
            self._format_value(last_lap_fuel, precision=1, suffix=" L"),
            anchor="rm",
            font=self.font_large,
            fill="black",
        )

        draw.text(
            (avg_card[0] + 20, avg_card[1] + 24),
            "AVG / LAP",
            anchor="lm",
            font=self.font_small,
            fill="black",
        )
        draw.text(
            (avg_card[2] - 20, avg_card[3] - 100),
            self._format_value(avg_per_lap, precision=1, suffix=" L"),
            anchor="rm",
            font=self.font_large,
            fill="black",
        )
