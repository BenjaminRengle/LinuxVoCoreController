from PIL import ImageFont


class QualifySummaryInfo:
    """Colored-tile review screen (see Screenshots/QualifySummary.png for the
    style this mirrors), showing what's needed to plan race fuel by hand
    right after qualifying: best lap time, finishing position, and average
    fuel burned per lap.
    """

    def __init__(self):
        self.font_title = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            40
        )

        self.font_label = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            20
        )

        self.font_value_large = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            52
        )

        self.font_value_medium = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            32
        )

        self.font_value_position = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            48
        )

    def _laptime_seconds(self, lap_time):
        if lap_time is None:
            return None
        return (
            lap_time.hours * 3600
            + lap_time.minutes * 60
            + lap_time.seconds
            + lap_time.fraction / 1000.0
        )

    def _format_time(self, lap_time):
        total_seconds = self._laptime_seconds(lap_time)
        if not total_seconds or total_seconds <= 0:
            return "--:--.---"

        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
        milliseconds = max(0, min(999, milliseconds))
        return f"{minutes}:{seconds:02d}.{milliseconds:03d}"

    def _format_position(self, position):
        if not position:
            return "--"
        return str(int(position))

    def _format_fuel_per_lap(self, fuel_per_lap):
        if fuel_per_lap is None:
            return "-- L"
        return f"{fuel_per_lap:.2f} L"

    def _draw_tile(self, draw, box, label, value, bg_color, text_color, value_font):
        x0, y0, x1, y1 = box
        draw.rounded_rectangle(box, radius=20, fill=bg_color)
        draw.text(
            (x0 + 24, y0 + 20),
            label,
            anchor="la",
            font=self.font_label,
            fill=text_color,
        )
        draw.text(
            ((x0 + x1) / 2, y1 - 30),
            value,
            anchor="mm",
            font=value_font,
            fill=text_color,
        )

    def draw(self, draw, best_lap, position, fuel_per_lap):
        """Render the qualifying review screen.

        Args:
            draw: PIL ImageDraw object
            best_lap: LapTime struct (or None) - the session's best lap
            position: int race/qualifying position (or None)
            fuel_per_lap: float liters/lap average (or None)
        """
        draw.rectangle((0, 0, 800, 480), fill=(0, 0, 0))

        draw.text(
            (400, 36),
            "QUALIFYING REVIEW",
            anchor="ma",
            font=self.font_title,
            fill="white",
        )

        margin_left = 170
        margin_right = 80
        gap = 20

        best_lap_box = (margin_left, 110, 800 - margin_right, 280)
        self._draw_tile(
            draw,
            best_lap_box,
            "BEST LAP TIME",
            self._format_time(best_lap),
            (150, 60, 200),
            "white",
            self.font_value_large,
        )

        bottom_top = 300
        bottom_bottom = 450
        half_width = (800 - margin_left - margin_right - gap) / 2

        position_box = (margin_left, bottom_top, margin_left + half_width, bottom_bottom)
        self._draw_tile(
            draw,
            position_box,
            "POSITION",
            self._format_position(position),
            (255, 255, 255),
            "black",
            self.font_value_position,
        )

        fuel_box = (margin_left + half_width + gap, bottom_top, 800 - margin_right, bottom_bottom)
        self._draw_tile(
            draw,
            fuel_box,
            "FUEL / LAP",
            self._format_fuel_per_lap(fuel_per_lap),
            (40, 180, 40),
            "white",
            self.font_value_medium,
        )
