import logging

from PIL import ImageFont

logger = logging.getLogger(__name__)


class DeltaInfo:
    """Tracks a time-vs-track-position trace of the fastest clean lap this
    session and uses it to compute a live delta and a projected lap time.

    Lacking any built-in delta/predicted-lap data from the sim, this
    interpolates against the fastest clean (non-pit) lap recorded so far:
    every tick the current lap's (track position, time-into-lap) is sampled,
    and on each lap completion that trace becomes the new reference if it
    was clean and faster than the current one. The live delta is then just
    "time into this lap" minus "reference time at this same track position".
    """

    def __init__(self):
        self.font_delta = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            89
        )

        self.font_label = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            28
        )

        self.font_small = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Regular.ttf",
            24
        )

        self.font_value = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            52
        )

        self._last_lap_num = None
        self._current_samples = []
        self._pit_seen_this_lap = False
        self._reference_samples = None
        self._reference_total_time = None

    def _laptime_seconds(self, lap_time):
        """Convert a LapTime struct (hours/minutes/seconds/fraction) to seconds."""
        if lap_time is None:
            return None
        return (
            lap_time.hours * 3600
            + lap_time.minutes * 60
            + lap_time.seconds
            + lap_time.fraction / 1000.0
        )

    def _car_in_pit(self, sim_data):
        """Whether the player's car is currently in the pits/garage."""
        car_data = getattr(sim_data, "playercardata", None)
        if car_data is None:
            return False
        return bool(getattr(car_data, "inpit", False)) or bool(
            getattr(car_data, "ingarage", False)
        )

    def record_sample(self, sim_data):
        """Sample (track position, time-into-lap) for the current lap.

        Must be called every telemetry tick regardless of which widget is
        currently displayed, so the reference lap and delta stay live even
        while a different widget is on screen.
        """
        if sim_data is None:
            return

        current_lap_num = getattr(sim_data, "lap", None)
        spline = getattr(sim_data, "playerspline", None)
        time_into_lap = self._laptime_seconds(getattr(sim_data, "currentlap", None))

        if current_lap_num is None or spline is None or time_into_lap is None:
            return

        spline = max(0.0, min(1.0, float(spline)))

        if self._last_lap_num is None:
            self._last_lap_num = current_lap_num
            self._current_samples = [(spline, time_into_lap)]
            self._pit_seen_this_lap = self._car_in_pit(sim_data)
            return

        self._pit_seen_this_lap = self._pit_seen_this_lap or self._car_in_pit(sim_data)

        if current_lap_num != self._last_lap_num:
            # A genuine lap completion means the last sample recorded was
            # near the finish line (spline ~1.0). If the lap number changed
            # while we were still early in the lap, it's a spurious/glitchy
            # reading (e.g. a transient telemetry misread) rather than a
            # real lap boundary - discard the fragment instead of finalizing
            # a bogus reference lap from a handful of samples.
            last_spline = self._current_samples[-1][0] if self._current_samples else 0.0
            if last_spline >= 0.9:
                self._finalize_lap(sim_data)
            self._last_lap_num = current_lap_num
            self._current_samples = [(0.0, 0.0)]
            self._pit_seen_this_lap = self._car_in_pit(sim_data)
        else:
            self._current_samples.append((spline, time_into_lap))

    def _finalize_lap(self, sim_data):
        """Promote the lap that just ended to the reference lap if it
        qualifies (clean, complete, and faster than the current reference)."""
        lastlap_seconds = self._laptime_seconds(getattr(sim_data, "lastlap", None))
        if (
            lastlap_seconds is None
            or lastlap_seconds <= 0
            or self._pit_seen_this_lap
            or len(self._current_samples) < 3
        ):
            return

        # Guard against a wrapped/out-of-order tail sample (e.g. the track
        # spline resetting to ~0.0 for a tick before the lap-number flip is
        # observed) - the binary search in _interpolate_reference_time
        # assumes samples are sorted ascending by spline, so a stray point
        # here would silently corrupt lookups for the rest of the session.
        samples = []
        for point in self._current_samples:
            if samples and point[0] < samples[-1][0]:
                continue
            samples.append(point)
        samples.append((1.0, lastlap_seconds))

        if self._reference_total_time is None or lastlap_seconds < self._reference_total_time:
            self._reference_samples = samples
            self._reference_total_time = lastlap_seconds
            logger.info(
                "New reference lap: %.3f s over %d samples",
                lastlap_seconds,
                len(samples),
            )

    def _interpolate_reference_time(self, spline):
        samples = self._reference_samples
        if not samples:
            return None
        if spline <= samples[0][0]:
            return samples[0][1]
        if spline >= samples[-1][0]:
            return samples[-1][1]

        lo, hi = 0, len(samples) - 1
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if samples[mid][0] <= spline:
                lo = mid
            else:
                hi = mid

        s0, t0 = samples[lo]
        s1, t1 = samples[hi]
        if s1 <= s0:
            return t0
        fraction = (spline - s0) / (s1 - s0)
        return t0 + fraction * (t1 - t0)

    def get_delta(self, sim_data):
        """Seconds vs. the reference lap at the same track position.

        Negative means ahead of the reference lap, positive means behind.
        Returns None until a reference lap exists (first clean lap of the
        session).
        """
        if sim_data is None or not self._reference_samples:
            return None

        spline = getattr(sim_data, "playerspline", None)
        time_into_lap = self._laptime_seconds(getattr(sim_data, "currentlap", None))
        if spline is None or time_into_lap is None:
            return None

        reference_time = self._interpolate_reference_time(max(0.0, min(1.0, float(spline))))
        if reference_time is None:
            return None
        return time_into_lap - reference_time

    def get_estimated_lap_seconds(self, sim_data):
        """Projected total lap time if the current delta trend holds to the line."""
        delta = self.get_delta(sim_data)
        if delta is None or self._reference_total_time is None:
            return None
        return self._reference_total_time + delta

    def _format_delta(self, delta):
        if delta is None:
            return "--.---"
        return f"{delta:+.3f}"

    def _bar_color(self, delta):
        if delta is None:
            return (150, 150, 150)
        return (140, 205, 60) if delta <= 0 else (220, 70, 70)

    def _text_color_for_background(self, bg_color):
        """Pick black or white text for readable contrast on a chip color."""
        r, g, b = bg_color
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        return (20, 20, 20) if luminance > 140 else (245, 245, 245)

    def _draw_chip(self, draw, x, y, width, height, text, bg_color, font):
        """Draw a rounded, filled label pill with centered text."""
        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=height / 2,
            fill=bg_color,
        )
        draw.text(
            (x + width / 2, y + height / 2),
            text,
            anchor="mm",
            font=font,
            fill=self._text_color_for_background(bg_color),
        )

    def _format_time(self, lap_time):
        if lap_time is None:
            return "--:--.---"

        total_seconds = self._laptime_seconds(lap_time)
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
        milliseconds = max(0, min(999, milliseconds))

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"

    def draw(
        self,
        draw,
        x,
        y,
        delta,
        lap_time=None,
        estimated_lap=None,
        last_lap=None,
        best_lap=None,
        bar_fraction=0.6,
        label="",
    ):
        """Draw current delta information and lap timing details."""
        width = 640
        height = 460
        padding = 20

        background_color = (10, 10, 10)
        frame_color = (60, 60, 60)
        accent_color = self._bar_color(delta)

        draw.rounded_rectangle(
            (x, y, x + width, y + height),
            radius=24,
            fill=background_color,
            outline=frame_color,
            width=2,
        )

        # Big delta readout, centered.
        delta_text = self._format_delta(delta)
        draw.text(
            (x + width / 2, y + 4),
            delta_text,
            anchor="ma",
            font=self.font_delta,
            fill="white",
        )

        # Reference-lap progress bar with sector tick marks, echoing a
        # delta-bar HUD readout.
        bar_height = 22
        bar_x = x + padding
        bar_y = y + padding + 96
        bar_width = width - padding * 2

        draw.rounded_rectangle(
            (bar_x, bar_y, bar_x + bar_width, bar_y + bar_height),
            radius=bar_height / 2,
            outline=frame_color,
            width=2,
            fill=(0, 0, 0),
        )

        filled_width = max(0, min(bar_width, int(bar_width * bar_fraction)))
        if filled_width > 0:
            draw.rounded_rectangle(
                (bar_x, bar_y, bar_x + filled_width, bar_y + bar_height),
                radius=bar_height / 2,
                fill=accent_color,
            )

        for fraction in (0.25, 0.5, 0.75):
            tick_x = bar_x + bar_width * fraction
            draw.line(
                (tick_x, bar_y, tick_x, bar_y + bar_height),
                fill=(230, 230, 230),
                width=2,
            )

        # Colored label chips + big values for each timing row.
        info_rows = [
            ("LAP TIMER", self._format_time(lap_time), (0, 200, 235)),
            ("EST. LAP", self._format_time(estimated_lap), (110, 210, 60)),
            ("LAST LAP", self._format_time(last_lap), (235, 195, 40)),
            ("BEST LAP", self._format_time(best_lap), (150, 60, 200)),
        ]

        rows_top = bar_y + bar_height + 36
        rows_bottom = y + height - padding
        row_height = (rows_bottom - rows_top) / len(info_rows)
        chip_row_width = 220
        chip_row_height = min(50, row_height - 10)

        for index, (row_label, row_value, chip_color) in enumerate(info_rows):
            row_center_y = rows_top + row_height * index + row_height / 2
            self._draw_chip(
                draw,
                x + padding,
                row_center_y - chip_row_height / 2,
                chip_row_width,
                chip_row_height,
                row_label,
                chip_color,
                self.font_label,
            )
            draw.text(
                (x + width - padding, row_center_y),
                row_value,
                anchor="rm",
                font=self.font_value,
                fill="white",
            )
