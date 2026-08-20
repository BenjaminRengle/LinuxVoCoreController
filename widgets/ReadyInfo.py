from PIL import ImageFont


class ReadyInfo:
    """Static idle screen (see Screenshots/ready.png) shown in place of a
    blank black display whenever there's no live telemetry to render -
    e.g. still in the sim's menus, or waiting for a session to start.
    """

    def __init__(self):
        self.font_ready = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-ExtraBold.ttf",
            130
        )

        self.font_logo = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-ExtraBold.ttf",
            34
        )

        self.font_tagline = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            18
        )

    def draw(self, draw):
        """Render the static idle/ready screen."""
        draw.rectangle((0, 0, 800, 480), fill=(0, 0, 0))

        draw.text(
            (440, 220),
            "READY",
            anchor="mm",
            font=self.font_ready,
            fill="white",
        )

        draw.text(
            (760, 400),
            "LOGICRANK",
            anchor="rm",
            font=self.font_logo,
            fill=(210, 30, 30),
        )

        draw.text(
            (760, 434),
            "DRIVER INFO DISPLAY",
            anchor="rm",
            font=self.font_tagline,
            fill="white",
        )
