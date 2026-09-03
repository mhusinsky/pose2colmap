import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from pose2colmap import cameras_line, load_intrinsic_txt, resolve_intrinsics


def write_png(path: Path, width: int, height: int) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    raw = b"\x00" + (b"\x00\x00\x00" * width)
    idat = zlib.compress(raw * height)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


class ResolveIntrinsicsTests(unittest.TestCase):
    def setUp(self):
        self.matrix_txt = (
            "1482.1878662109 0 3149.0000000000\n"
            "0 1481.4029541016 4198.5000000000\n"
            "0 0 1\n"
        )

    def _load_txt_params(self, root: Path):
        txt = root / "left_undistort_intrinsic.txt"
        txt.write_text(self.matrix_txt, encoding="utf-8")
        return load_intrinsic_txt(str(txt))

    def test_matrix_parser_rejects_non_intrinsic_triples(self):
        with tempfile.TemporaryDirectory() as td:
            txt = Path(td) / "left_undistort_intrinsic.txt"
            txt.write_text("1 2 3\n4 5 6\n7 8 9\n", encoding="utf-8")
            self.assertEqual(load_intrinsic_txt(str(txt)), {})

    def test_matrix_txt_selected_over_opt_and_json_with_alias_dims(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt_params = self._load_txt_params(root)
            frames = [{
                "file_path": "left/frame_0001.png",
                "fl_x": 9999.0,
                "fl_y": 9999.0,
                "cx": 10.0,
                "cy": 20.0,
                "width": 6298,
                "height": 8397,
            }]
            opt_params = {
                "FocalLength": 35.0,
                "SensorSize": 36.0,
                "ImageWidth": 1111,
                "ImageHeight": 2222,
            }

            model, fx, fy, cx, cy, *_rest, w, h = resolve_intrinsics(
                frames,
                txt_params,
                opt_params,
                label="left",
                image_dir=root / "left",
            )

            self.assertEqual(model, "PINHOLE")
            self.assertEqual((w, h), (6298, 8397))
            self.assertEqual(fx, 1482.1878662109)
            self.assertEqual(fy, 1481.4029541016)
            self.assertEqual(cx, 3149.0)
            self.assertEqual(cy, 4198.5)

            line = cameras_line(1, model, w, h, fx, fy, cx, cy, 0.0, 0.0, 0.0, 0.0, 0.0)
            self.assertEqual(
                line,
                "1 PINHOLE 6298 8397 1482.18786621 1481.40295410 3149.00000000 4198.50000000\n",
            )

    def test_matrix_txt_uses_imagewidth_alias(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt_params = self._load_txt_params(root)
            frames = [{"file_path": "left/frame_0001.png", "imageWidth": 7000, "imageHeight": 5000}]

            model, _fx, _fy, _cx, _cy, *_rest, w, h = resolve_intrinsics(
                frames,
                txt_params,
                {},
                label="left",
                image_dir=root / "left",
            )

            self.assertEqual(model, "PINHOLE")
            self.assertEqual((w, h), (7000, 5000))

    def test_matrix_txt_uses_image_file_dimensions(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt_params = self._load_txt_params(root)
            image_path = root / "left" / "frame_0001.png"
            write_png(image_path, 123, 45)
            frames = [{"file_path": "left/frame_0001.png"}]

            model, _fx, _fy, _cx, _cy, *_rest, w, h = resolve_intrinsics(
                frames,
                txt_params,
                {},
                label="left",
                image_dir=root / "left",
            )

            self.assertEqual(model, "PINHOLE")
            self.assertEqual((w, h), (123, 45))

    def test_matrix_txt_missing_dimensions_fails_without_opt_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            txt_params = self._load_txt_params(root)
            frames = [{"file_path": "left/missing.png"}]
            opt_params = {
                "FocalLength": 35.0,
                "SensorSize": 36.0,
                "ImageWidth": 6000,
                "ImageHeight": 4000,
            }

            with self.assertRaisesRegex(ValueError, "Refusing to fall back to \\.opt"):
                resolve_intrinsics(
                    frames,
                    txt_params,
                    opt_params,
                    label="left",
                    image_dir=root / "left",
                )


if __name__ == "__main__":
    unittest.main()
