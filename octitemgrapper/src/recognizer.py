from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

import cv2
import numpy as np

from templates_loader import TemplateEntry


@dataclass
class RecognizedItem:
    name: str
    score: float
    method: str  # "orb" or "corr"


class ORBItemRecognizer:
    def __init__(self, templates: Dict[str, TemplateEntry]) -> None:
        self.templates = templates
        self.orb = cv2.ORB_create(nfeatures=500)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self._tpl_gray: Dict[str, np.ndarray] = {}
        self._tpl_kp: Dict[str, Tuple[Tuple[cv2.KeyPoint, ...], np.ndarray]] = {}
        for name, entry in templates.items():
            gray = cv2.cvtColor(entry.image_bgr, cv2.COLOR_BGR2GRAY)
            self._tpl_gray[name] = gray
            kp, des = self.orb.detectAndCompute(gray, None)
            if des is None:
                des = np.zeros((0, 32), dtype=np.uint8)
            self._tpl_kp[name] = (tuple(kp), des)

    def recognize(self, roi_bgr: np.ndarray) -> RecognizedItem:
        gray = cv2.cvtColor(roi_bgr, cv2.COLOR_BGR2GRAY)
        kp, des = self.orb.detectAndCompute(gray, None)
        if des is None or len(kp) == 0:
            return self._fallback_template_match(gray)

        best_name: str = "Unknown"
        best_score: float = -1.0

        for name, (tpl_kp, tpl_des) in self._tpl_kp.items():
            if tpl_des is None or tpl_des.shape[0] == 0:
                continue
            matches = self.bf.knnMatch(tpl_des, des, k=2)
            good = []
            for m, n in matches:
                if m.distance < 0.75 * n.distance:
                    good.append(m)
            score = float(len(good))
            if score > best_score:
                best_score = score
                best_name = name

        # If score too low, try fallback template matching as a second opinion
        if best_score < 8:
            fb = self._fallback_template_match(gray)
            # Prefer correlation if it is confident enough
            if fb.score >= 0.5:
                return fb
        return RecognizedItem(name=best_name, score=best_score, method="orb")

    def _fallback_template_match(self, gray_roi: np.ndarray) -> RecognizedItem:
        best_name = "Unknown"
        best_val = -1.0
        for name, tpl_gray in self._tpl_gray.items():
            try:
                tpl_resized = cv2.resize(
                    tpl_gray, (gray_roi.shape[1], gray_roi.shape[0]), interpolation=cv2.INTER_AREA
                )
            except Exception:
                continue
            res = cv2.matchTemplate(gray_roi, tpl_resized, cv2.TM_CCOEFF_NORMED)
            val = float(res[0, 0])
            if val > best_val:
                best_val = val
                best_name = name
        return RecognizedItem(name=best_name, score=best_val, method="corr") 