from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import cv2
import numpy as np


@dataclass
class TemplateEntry:
    name: str
    image_bgr: np.ndarray


def load_templates(directory: Path) -> Dict[str, TemplateEntry]:
    supported_ext = {".png", ".jpg", ".jpeg", ".bmp"}
    templates: Dict[str, TemplateEntry] = {}
    for path in sorted(directory.glob("*")):
        if path.suffix.lower() not in supported_ext:
            continue
        name = path.stem
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            continue
        templates[name] = TemplateEntry(name=name, image_bgr=img)
    return templates 