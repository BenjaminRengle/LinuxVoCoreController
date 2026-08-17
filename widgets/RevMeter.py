from PIL import ImageFont

class RevMeter:

    def __init__(self):

        self.font_gear = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            180
        )

        self.font_speed = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Regular.ttf",
            70
        )

        self.font_small = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Light.ttf",
            32
        )

    def draw(self, draw, rpm, gear, speed, max_rpm):

        if gear == 0:
            gear = "N"

        fraction = max(0.0, min(rpm / max_rpm, 1.0))

        # Top black area shrinks as RPM increases
        top = int(480 * (1.0 - fraction))

        draw.rounded_rectangle(
            (160, 30, 780, 460),
            radius=25,
            fill=(0,0,0)
        )

        warning_threshold = 0.95
        if fraction >= warning_threshold:
            fill_color = (255, 0, 0)
        else:
            fill_color = (255, 140, 0)

        draw.rectangle(
            (160, top, 780, 480),
            fill=fill_color
        )

        draw.text(
            (470,220),
            str(gear),
            anchor="mm",
            font=self.font_gear,
            fill="white"
        )

        draw.text(
            (470,360),
            "SPEED (KM/H)",
            anchor="mm",
            font=self.font_small,
            fill="white"
        )

        draw.text(
            (470,420),
            str(speed),
            anchor="mm",
            font=self.font_speed,
            fill="white"
        )