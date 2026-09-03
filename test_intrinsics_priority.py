import tempfile
import unittest
from pathlib import Path

from pose2colmap import cameras_line, load_intrinsic_txt, resolve_intrinsics


class IntrinsicsPriorityTests(unittest.TestCase):
    def _write_intrinsic_txt(self, content: str) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "left_undistort_intrinsic.txt"
            path.write_text(content, encoding="utf-8")
            return load_intrinsic_txt(str(path))

    def test_intrinsic_txt_uses_pinhole_and_preserves_fx_fy(self):
        frames = [{"w": 4032, "h": 3024, "fl_x": 9999.0, "fl_y": 9998.0, "cx": 2000.0, "cy": 1500.0}]
        intr = self._write_intrinsic_txt("fx=3210.5\nfy=3199.25\ncx=2016.0\ncy=1512.0\nw=4032\nh=3024\n")
        model, fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6, w, h = resolve_intrinsics(
            frames, intr, {}, label="left", fisheye=False
        )
        self.assertEqual(model, "PINHOLE")
        self.assertEqual((fx, fy, cx, cy, w, h), (3210.5, 3199.25, 2016.0, 1512.0, 4032, 3024))
        line = cameras_line(1, model, w, h, fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6).strip()
        self.assertEqual(line, "1 PINHOLE 4032 3024 3210.50000000 3199.25000000 2016.00000000 1512.00000000")

    def test_intrinsic_txt_precedes_json_for_non_fisheye(self):
        frames = [{"w": 4032, "h": 3024, "fl_x": 2800.0, "fl_y": 2801.0, "cx": 2000.0, "cy": 1500.0}]
        intr = self._write_intrinsic_txt("fx=3500.0\nfy=3400.0\ncx=2010.0\ncy=1505.0\nw=4032\nh=3024\n")
        model, fx, fy, cx, cy, *_ = resolve_intrinsics(frames, intr, {}, label="left", fisheye=False)
        self.assertEqual(model, "PINHOLE")
        self.assertEqual((fx, fy, cx, cy), (3500.0, 3400.0, 2010.0, 1505.0))

    def test_json_fallback_when_intrinsic_txt_missing(self):
        frames = [{
            "w": 4032, "h": 3024,
            "fl_x": 2800.0, "fl_y": 2795.0,
            "cx": 2010.0, "cy": 1510.0,
            "k1": 0.01, "k2": -0.02, "k3": 0.003, "p1": 0.0001, "p2": -0.0002
        }]
        model, fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6, w, h = resolve_intrinsics(
            frames, {}, {}, label="left", fisheye=False
        )
        self.assertEqual(model, "FULL_OPENCV")
        self.assertEqual((fx, fy, cx, cy, k1, k2, p1, p2, k3, k4, k5, k6, w, h),
                         (2800.0, 2795.0, 2010.0, 1510.0, 0.01, -0.02, 0.0001, -0.0002, 0.003, 0.0, 0.0, 0.0, 4032, 3024))


if __name__ == "__main__":
    unittest.main()
