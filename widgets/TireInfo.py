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

    def _draw_tire_bars(self, draw, x, y, wear, temp):
        """Draw visual tire tread bars with rounded outer edges and flat inner edges."""
        bar_height = 100
        bar_width = 20
        bar_spacing = 4
        radius = min(10, bar_height // 2)

        normalized_wear = self._normalize_wear(wear)
        color = self._get_tire_color(normalized_wear)

        for i in range(3):
            bx = x - bar_spacing - (i + 1) * (bar_width + bar_spacing)

            if i == 2:  # Leftmost bar: round the outer left edge
                draw.rectangle((bx + radius, y, bx + bar_width, y + bar_height), fill=color)
                draw.ellipse((bx, y, bx + 2 * radius, y + bar_height), fill=color)
            elif i == 0:  # Rightmost bar: round the outer right edge
                draw.rectangle((bx, y, bx + bar_width - radius, y + bar_height), fill=color)
                draw.ellipse((bx + bar_width - 2 * radius, y, bx + bar_width, y + bar_height), fill=color)
            else:  # Middle bar stays straight
                draw.rectangle((bx, y, bx + bar_width, y + bar_height), fill=color)

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

        # Tire positions: FL, FR, RL, RR
        tire_positions = [
            (400, 50),  # FL
            (710, 50),  # FR
            (400, 250),  # RL
            (710, 250)   # RR
        ]
        labels = ["FL", "FR", "RL", "RR"]

        # Draw each tire with its data
        for idx, (x, y) in enumerate(tire_positions):
            pressure = tyre_pressure[idx] if idx < len(tyre_pressure) else 0.0
            temp = tyre_temp[idx] if idx < len(tyre_temp) else 0.0
            wear = tyre_wear[idx] if idx < len(tyre_wear) else 0.0

            normalized_wear = self._normalize_wear(wear)

            # Draw tire visual bars
            self._draw_tire_bars(draw, x + 20, y + 20, normalized_wear, temp)

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
                (x -30, y + 140),
                f"{pressure:.0f} psi",
                anchor="mm",
                font=self.font_medium,
                fill="white"
            )

        # Age or lap info
        # draw.text(
        #     (center_x, center_y),
        #     "AGE: 1 LAP" if laps == 0 else f"AGE: {laps} LAP",
        #     anchor="mm",
        #     font=self.font_small,
        #     fill=(150, 150, 150)
        # )
