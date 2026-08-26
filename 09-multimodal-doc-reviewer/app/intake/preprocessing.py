"""Image preprocessing for uploaded raster pages (Phase 1, step 3):
rotation correction, contrast enhancement, noise removal, and a resolution
sanity check. Every step is recorded in `PreprocessingStep` metadata so a
reviewer can see what was done to a page before OCR ran on it.
"""
from __future__ import annotations

from PIL import Image, ImageFilter, ImageOps

from app.intake.models import PreprocessingStep


def _correct_rotation(image: Image.Image) -> tuple[Image.Image, PreprocessingStep]:
    orientation = image.getexif().get(0x0112, 1)
    corrected = ImageOps.exif_transpose(image) or image
    if orientation != 1:
        detail = f"corrected EXIF orientation tag {orientation} -> upright {corrected.size[0]}x{corrected.size[1]}"
    else:
        detail = "no EXIF orientation tag present; image already upright"
    return corrected, PreprocessingStep(name="rotation_correction", detail=detail)


def _enhance_contrast(image: Image.Image) -> tuple[Image.Image, PreprocessingStep]:
    enhanced = ImageOps.autocontrast(image.convert("RGB"))
    return enhanced, PreprocessingStep(name="contrast_enhancement", detail="applied autocontrast")


def _remove_noise(image: Image.Image) -> tuple[Image.Image, PreprocessingStep]:
    denoised = image.filter(ImageFilter.MedianFilter(size=3))
    return denoised, PreprocessingStep(name="noise_removal", detail="applied 3x3 median filter")


def _check_resolution(
    image: Image.Image, min_width: int, min_height: int
) -> tuple[PreprocessingStep, list[str]]:
    width, height = image.size
    step = PreprocessingStep(name="resolution_check", detail=f"{width}x{height} px")
    warnings: list[str] = []
    if width < min_width or height < min_height:
        warnings.append(
            f"low_resolution: {width}x{height} is below the {min_width}x{min_height} minimum; "
            "OCR accuracy may suffer"
        )
    return step, warnings


def preprocess_image(
    image: Image.Image, min_width: int, min_height: int
) -> tuple[Image.Image, list[PreprocessingStep], list[str]]:
    steps: list[PreprocessingStep] = []

    image, step = _correct_rotation(image)
    steps.append(step)

    image, step = _enhance_contrast(image)
    steps.append(step)

    image, step = _remove_noise(image)
    steps.append(step)

    step, warnings = _check_resolution(image, min_width, min_height)
    steps.append(step)

    return image, steps, warnings
