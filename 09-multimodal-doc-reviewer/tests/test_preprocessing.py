import io

from PIL import Image

from app.intake.preprocessing import preprocess_image


def _make_image(width=800, height=1000, exif_orientation=None):
    image = Image.new("RGB", (width, height), color=(200, 200, 200))
    if exif_orientation is not None:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        buf = io.BytesIO()
        image.save(buf, format="JPEG", exif=exif.tobytes())
        buf.seek(0)
        image = Image.open(buf)
        image.load()
    return image


def test_pipeline_runs_all_four_steps():
    image = _make_image()
    _, steps, _ = preprocess_image(image, min_width=600, min_height=600)
    assert [s.name for s in steps] == [
        "rotation_correction",
        "contrast_enhancement",
        "noise_removal",
        "resolution_check",
    ]


def test_rotation_correction_notes_missing_exif():
    image = _make_image(exif_orientation=None)
    _, steps, _ = preprocess_image(image, min_width=600, min_height=600)
    assert "no EXIF orientation tag" in steps[0].detail


def test_rotation_correction_applies_exif_orientation():
    image = _make_image(exif_orientation=6)
    _, steps, _ = preprocess_image(image, min_width=600, min_height=600)
    assert "corrected EXIF orientation tag 6" in steps[0].detail


def test_low_resolution_warns():
    image = _make_image(width=200, height=200)
    _, _, warnings = preprocess_image(image, min_width=600, min_height=600)
    assert any("low_resolution" in w for w in warnings)


def test_high_resolution_has_no_warning():
    image = _make_image(width=1200, height=1600)
    _, _, warnings = preprocess_image(image, min_width=600, min_height=600)
    assert warnings == []
