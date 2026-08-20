from PIL import ImageFont


class TireInfo:

    def __init__(self):
        self.font_large = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            48
        )

        self.font_medium = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            32
        )

        self.font_small = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Regular.ttf",
            24
        )

        self.font_tiny = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Light.ttf",
            18
        )

    def _normalize_wear(self, wear):
        """Normalize tire wear to a percentage value."""
        if wear <= 1.0:
            return wear * 100.0
        return wear

    def _get_tire_color(self, wear):
        """Return color based on tire wear percentage."""
        if wear > 90:
            return (0, 200, 0)  # Green: good
        elif wear > 60:
            return (255, 200, 0)  # Yellow/Orange: medium
        else:
            return (200, 50, 50)  # Red: worn

    def _get_compound_color(self, compound):
        """Return a color for a tire compound name (wet/medium/hard/soft)."""
        name = compound.lower()
        if "wet" in name:
            return (60, 140, 255)  # Blue
        elif "medium" in name:
            return (230, 210, 40)  # Yellow
        elif "hard" in name:
            return (220, 60, 60)  # Red
        elif "soft" in name:
            return (160, 160, 160)  # Gray
        return (200, 200, 200)

    def _draw_tire_bars(self, draw, x, y, wear, temp):
        """Draw a tire as a single rounded tread block with two thin gaps
        splitting it into three segments, rather than three separate pills."""
        tire_width = 100
        tire_height = 120
        radius = 20
        gap_width = 6

        normalized_wear = self._normalize_wear(wear)
        color = self._get_tire_color(normalized_wear)

        left = x - tire_width
        right = x
        top = y
        bottom = y + tire_height

        draw.rounded_rectangle((left, top, right, bottom), radius=radius, fill=color)

        segment_width = tire_width / 3
        for i in (1, 2):
            gap_x = left + segment_width * i
            draw.rectangle(
                (gap_x - gap_width / 2, top, gap_x + gap_width / 2, bottom),
                fill=(0, 0, 0),
            )

    def draw(self, draw, tyre_pressure, tyre_temp, tyre_wear, tyre_slip, compound="", laps=0):
        """
        Render a visual tire status display on the VoCore screen.

        Parameters:
            draw: PIL ImageDraw object
            tyre_pressure: iterable of 4 pressure values [FL, FR, RL, RR]
            tyre_temp: iterable of 4 temperature values [FL, FR, RL, RR]
            tyre_wear: iterable of 4 wear percentages [FL, FR, RL, RR]
            tyre_slip: iterable of 4 slip values [FL, FR, RL, RR]
            compound: tire compound name (optional)
            laps: number of laps (optional)
        """

        # Draw background
        draw.rectangle((0, 0, 800, 480), fill=(0, 0, 0))

        # Shift everything right a bit - the physical panel's bezel crops
        # a sliver off the left edge, cutting into the FL/RL wear% text.
        offset_x = 30

        # Tire positions: FL, FR, RL, RR
        tire_positions = [
            (400 + offset_x, 50),  # FL
            (710 + offset_x, 50),  # FR
            (400 + offset_x, 250),  # RL
            (710 + offset_x, 250)   # RR
        ]
        labels = ["FL", "FR", "RL", "RR"]

        # Draw each tire with its data
        for idx, (x, y) in enumerate(tire_positions):
            pressure = tyre_pressure[idx] if idx < len(tyre_pressure) else 0.0
            temp = tyre_temp[idx] if idx < len(tyre_temp) else 0.0
            wear = tyre_wear[idx] if idx < len(tyre_wear) else 0.0

            normalized_wear = self._normalize_wear(wear)

            # Draw tire visual bars
            self._draw_tire_bars(draw, x + 30, y + 20, normalized_wear, temp)

            # Draw wear (large, on the left)
            draw.text(
                (x - 80, y + 50),
                f"{normalized_wear:.1f} %",
                anchor="rm",
                font=self.font_large,
                fill="white"
            )

            # Draw temperature (on the left, below pressure)
            draw.text(
                (x - 80, y + 100),
                f"{temp:.0f}°C",
                anchor="rm",
                font=self.font_small,
                fill="white"
            )

            # Draw pressure (below tire visual)
            draw.text(
                (x -30, y + 165),
                f"{pressure:.0f} psi",
                anchor="mm",
                font=self.font_medium,
                fill="white"
            )

        # Compound, in the top-left corner (pushed right - the physical
        # panel's bezel crops a wide sliver off the left edge here)
        if compound:
            draw.text(
                (200, 20),
                f"{compound.upper()} COMPOUND",
                anchor="la",
                font=self.font_medium,
                fill=self._get_compound_color(compound)
            )
