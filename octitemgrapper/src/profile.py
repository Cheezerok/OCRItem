from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List

from roi_selector import Rect


@dataclass
class Profile:
    templates_dir: str
    rois: List[Rect]

    def to_json(self) -> str:
        obj = {
            "templates_dir": self.templates_dir,
            "rois": [asdict(r) for r in self.rois],
        }
        return json.dumps(obj, ensure_ascii=False, indent=2)

    @staticmethod
    def from_file(path: Path) -> "Profile":
        data = json.loads(path.read_text(encoding="utf-8"))
        rois = [Rect(**r) for r in data.get("rois", [])]
        return Profile(templates_dir=data.get("templates_dir", ""), rois=rois)

    def to_file(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(self.to_json(), encoding="utf-8")
        tmp.replace(path) 