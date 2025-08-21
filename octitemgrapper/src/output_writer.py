from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import List


class OutputWriter:
    def __init__(self, out_dir: Path) -> None:
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.txt_path = self.out_dir / "items.txt"
        self.json_path = self.out_dir / "items.json"

    def write(self, items: List[str]) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        # text
        tmp_txt = self.txt_path.with_suffix(".txt.tmp")
        tmp_txt.write_text("\n".join(items), encoding="utf-8")
        tmp_txt.replace(self.txt_path)
        # json
        payload = {"timestamp": ts, "items": items}
        tmp_json = self.json_path.with_suffix(".json.tmp")
        tmp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_json.replace(self.json_path)

    def write_for_zone(self, zone_index: int, items: List[str]) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        txt = self.out_dir / f"items_zone_{zone_index}.txt"
        jsn = self.out_dir / f"items_zone_{zone_index}.json"
        tmp_txt = txt.with_suffix(".txt.tmp")
        tmp_txt.write_text("\n".join(items), encoding="utf-8")
        tmp_txt.replace(txt)
        payload = {"timestamp": ts, "zone": zone_index, "items": items}
        tmp_json = jsn.with_suffix(".json.tmp")
        tmp_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp_json.replace(jsn) 