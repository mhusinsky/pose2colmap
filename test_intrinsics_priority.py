import tempfile
import unittest
from pathlib import Path

from pose2colmap import cameras_line, load_intrinsic_txt, resolve_intrinsics


class IntrinsicsPriorityTests(unittest.TestCase):
    def _write_intrinsics(self, content):
        tmpdir = tempfile.TemporaryDirectory()
        path = Path(tmpdir.name) / "left_undistort"
        path.write_text(content, encoding="utf-8")
        self.addCleanup(tmpdir.cleanup)
        return str(path)

    def test_load_intrinsic_txt_parses_s20_matrix(self):
        params = load_intrinsic_txt(self._write_intrinsics(
            "1423.5, 0, 2012.25\n"
            "0, 1419.75, 1501.5\n"
            "0, 0, 1\n"
        ))

        self.assertEqual(params["fx"], 1423.5)
        self.assertEqual(params["fy"], 1419.75)
        self.assertEqual(params["cx"], 2012.25)
        self.assertEqual(params["cy"], 1501.5)

    def test_resolve_intrinsics_prefers_matrix_txt_over_opt_and_json(self):
        params = load_intrinsic_txt(self._write_intrinsics(
            "1500 0 2000\n"
            "0 1490 1000\n"
            "0 0 1\n"
        ))
        frames = [{"w": 4000, "h": 3000, "fl_x": 9000.0, "fl_y": 9100.0, "cx": 10.0, "cy": 20.0}]
        opt_params = {
            "FocalLength": 35.0,
            "SensorSize": 36.0,
            "ImageWidth": 4000,
            "ImageHeight": 3000,
            "PrincipalPointX": 123.0,
            "PrincipalPointY": 456.0,
        }

        intrinsics = resolve_intrinsics(frames, params, opt_params, fisheye=False)

        self.assertEqual(intrinsics[0], "PINHOLE")
        self.assertEqual(intrinsics[1:5], (1500.0, 1490.0, 2000.0, 1000.0))
        self.assertEqual(intrinsics[-2:], (4000, 3000))

    def test_key_value_intrinsics_keep_precedence_over_matrix_rows(self):
        params = load_intrinsic_txt(self._write_intrinsics(
            "fx = 1100\n"
            "fy = 1110\n"
            "cx = 1200\n"
            "cy = 900\n"
            "width = 2448\n"
            "height = 2048\n"
            "1500 0 2000\n"
            "0 1490 1000\n"
            "0 0 1\n"
        ))

        self.assertEqual(params["fx"], 1100.0)
        self.assertEqual(params["fy"], 1110.0)
        self.assertEqual(params["cx"], 1200.0)
        self.assertEqual(params["cy"], 900.0)
        self.assertEqual(params["w"], 2448.0)
        self.assertEqual(params["h"], 2048.0)

        intrinsics = resolve_intrinsics([{"w": 9999, "h": 9999}], params, {}, fisheye=False)

        self.assertEqual(intrinsics[0], "PINHOLE")
        self.assertEqual(intrinsics[1:5], (1100.0, 1110.0, 1200.0, 900.0))
        self.assertEqual(intrinsics[-2:], (2448, 2048))

    def test_cameras_line_writes_pinhole_fx_and_fy(self):
        line = cameras_line(1, "PINHOLE", 4000, 3000, 1500.0, 1490.0, 2000.0, 1000.0, 0.0, 0.0, 0.0, 0.0, 0.0)

        self.assertEqual(
            line,
            "1 PINHOLE 4000 3000 1500.00000000 1490.00000000 2000.00000000 1000.00000000\n",
        )

    def test_resolve_intrinsics_empty_frames_raises_value_error(self):
        with self.assertRaises(ValueError):
            resolve_intrinsics([], {}, {}, fisheye=False)


if __name__ == "__main__":
    unittest.main()
