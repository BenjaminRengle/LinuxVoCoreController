from PIL import ImageFont


class LeaderboardInfo:
    """Renders a standings table windowed to the rows around the player's
    own position, mirroring the sim's own leaderboard overlay: a POS badge,
    driver name, purple best-lap time, and a +/- gap relative to the player.

    No car-logo assets are available here, so the "CAR" icon column from
    the reference overlay is left out.
    """

    VISIBLE_ROWS = 7

    def __init__(self):
        self.font_header = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            24
        )

        self.font_row = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            30
        )

        self.font_pos = ImageFont.truetype(
            "/usr/share/fonts/open-sans/OpenSans-Bold.ttf",
            24
        )

    def _format_time(self, lap_time):
        if lap_time is None:
            return "--:--.---"

        total_seconds = (
            lap_time.hours * 3600
            + lap_time.minutes * 60
            + lap_time.seconds
            + lap_time.fraction / 1000.0
        )
        if total_seconds <= 0:
            return "--:--.---"

        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(round((total_seconds - int(total_seconds)) * 1000))
        milliseconds = max(0, min(999, milliseconds))
        return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

    def _format_gap(self, gap_seconds):
        if gap_seconds is None:
            return ""
        return f"{gap_seconds:+.2f}"

    def build_standings(self, cars, player_place, visible_rows=None):
        """Turn a raw car list into the windowed, gap-annotated rows draw() expects.

        Args:
            cars: iterable of objects/dicts with place, driver, bestlap,
                timebehindleader (as populated in SimData.CarData).
            player_place: the player's own race position (1-indexed).
            visible_rows: how many rows to show, centered on the player.
        """
        visible_rows = visible_rows or self.VISIBLE_ROWS

        entries = []
        player_time_behind_leader = None
        for car in cars:
            place = int(getattr(car, "place", 0) or 0)
            if place <= 0:
                continue
            entries.append(car)
            if place == player_place:
                player_time_behind_leader = float(getattr(car, "timebehindleader", 0.0))

        entries.sort(key=lambda car: int(getattr(car, "place", 0)))

        half_window = visible_rows // 2
        start_index = 0
        for i, car in enumerate(entries):
            if int(getattr(car, "place", 0)) == player_place:
                start_index = max(0, min(len(entries) - visible_rows, i - half_window))
                break
        start_index = max(0, start_index)

        window = entries[start_index:start_index + visible_rows]

        standings = []
        for car in window:
            is_player = int(getattr(car, "place", 0)) == player_place
            gap = None
            if not is_player and player_time_behind_leader is not None:
                gap = float(getattr(car, "timebehindleader", 0.0)) - player_time_behind_leader
            standings.append({
                "place": int(getattr(car, "place", 0)),
                "driver": getattr(car, "driver", "") or "",
                "best_lap": getattr(car, "bestlap", None),
                "gap": gap,
                "is_player": is_player,
            })

        return standings

    def draw(self, draw, standings):
        """Render a windowed standings table.

        standings: ordered list (ascending place) of dicts, as produced by
        build_standings():
            {"place": int, "driver": str, "best_lap": LapTime or None,
             "gap": float seconds or None, "is_player": bool}
        """
        x, y = 150, 20
        width = 630
        row_height = 52
        header_height = 44

        total_height = header_height + row_height * len(standings)

        draw.rounded_rectangle(
            (x, y, x + width, y + total_height),
            radius=20,
            fill=(10, 10, 10),
        )

        draw.rounded_rectangle(
            (x, y, x + width, y + header_height + 20),
            radius=20,
            fill=(255, 255, 255),
        )
        draw.rectangle((x, y + header_height - 20, x + width, y + header_height), fill=(255, 255, 255))

        for label, hx in (("POS", x + 20), ("DRIVER", x + 90), ("BEST LAP", x + width - 260), ("GAP", x + width - 40)):
            anchor = "lm" if label != "GAP" else "rm"
            draw.text((hx, y + header_height / 2), label, anchor=anchor, font=self.font_header, fill="black")

        row_y = y + header_height
        for row in standings:
            row_bg = (55, 55, 55) if row["is_player"] else (10, 10, 10)
            draw.rectangle((x + 2, row_y, x + width - 2, row_y + row_height), fill=row_bg)

            badge_size = 40
            badge_top = row_y + row_height / 2 - badge_size / 2
            draw.rounded_rectangle(
                (x + 16, badge_top, x + 16 + badge_size, badge_top + badge_size),
                radius=8,
                fill=(60, 150, 150),
            )
            draw.text(
                (x + 16 + badge_size / 2, row_y + row_height / 2),
                str(row["place"]),
                anchor="mm",
                font=self.font_pos,
                fill="white",
            )

            draw.text(
                (x + 90, row_y + row_height / 2),
                row["driver"] or "-",
                anchor="lm",
                font=self.font_row,
                fill="white",
            )

            draw.text(
                (x + width - 100, row_y + row_height / 2),
                self._format_time(row["best_lap"]),
                anchor="rm",
                font=self.font_row,
                fill=(190, 140, 255),
            )

            draw.text(
                (x + width - 20, row_y + row_height / 2),
                self._format_gap(row["gap"]),
                anchor="rm",
                font=self.font_row,
                fill="white",
            )

            row_y += row_height
