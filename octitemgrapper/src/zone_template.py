from __future__ import annotations

from dataclasses import dataclass
from typing import List

from roi_selector import Rect


@dataclass
class NRect:
    x: float
    y: float
    width: float
    height: float


def to_abs(nr: NRect, width: int, height: int) -> Rect:
    return Rect(
        x=int(round(nr.x * width)),
        y=int(round(nr.y * height)),
        width=int(round(nr.width * width)),
        height=int(round(nr.height * height)),
    )


def from_abs(r: Rect, width: int, height: int) -> NRect:
    return NRect(
        x=r.x / float(width) if width else 0.0,
        y=r.y / float(height) if height else 0.0,
        width=r.width / float(width) if width else 0.0,
        height=r.height / float(height) if height else 0.0,
    )


def default_10(width: int, height: int) -> List[NRect]:
    # Place 10 equal squares across a centered row
    margin_x = 0.02
    margin_y = 0.75  # near bottom area by default
    total_w = 1.0 - 2 * margin_x
    zone_w = total_w / 10.0 * 0.95
    gap = (total_w - zone_w * 10.0) / 9.0 if 10 > 1 else 0.0
    zone_h = zone_w  # square
    y = margin_y - zone_h / 2.0
    zones: List[NRect] = []
    x = margin_x
    for _ in range(10):
        zones.append(NRect(x=x, y=y, width=zone_w, height=zone_h))
        x += zone_w + gap
    return zones


def mlbb_scoreboard_10() -> List[NRect]:
    # Approximate layout for 10 players (5 left, 5 right) on a scoreboard
    # Zones cover the items area per row.
    zones: List[NRect] = []
    # Vertical layout: 5 rows per side
    top = 0.17
    row_h = 0.13
    z_h = 0.09
    # Left side items region (center-left)
    x_left = 0.30
    z_w = 0.20
    # Right side items region (center-right)
    x_right = 0.52
    for i in range(5):
        cy = top + i * row_h
        y = cy - z_h / 2.0
        zones.append(NRect(x=x_left, y=y, width=z_w, height=z_h))
    for i in range(5):
        cy = top + i * row_h
        y = cy - z_h / 2.0
        zones.append(NRect(x=x_right, y=y, width=z_w, height=z_h))
    return zones 