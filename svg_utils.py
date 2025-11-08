"""Utilities for converting SVG assets into raster images with WeChat-friendly fonts."""
from __future__ import annotations

import re
from pathlib import Path

try:  # pragma: no cover - external dependency
    import pyvips  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover - defer failure until use
    pyvips = None

SVG_FONT_FAMILIES = [
    "PingFang SC",
    "Heiti SC",
    "STHeiti",
    "Hiragino Sans GB",
    "Microsoft YaHei",
    "SimHei",
    "Source Han Sans SC",
    "Noto Sans CJK SC",
    "WenQuanYi Micro Hei",
]

SVG_TAG_PATTERN = re.compile(r"(<svg[^>]*>)", re.IGNORECASE)


def _build_font_fallback_css() -> str:
    families = SVG_FONT_FAMILIES + ["sans-serif"]
    family_stack = ", ".join('\"{}\"'.format(name) for name in families)
    return (
        "text, tspan, foreignObject, *, .t, .f { font-family: %s !important; }"
        % family_stack
    )


def _load_svg_with_fallback(svg_path: Path) -> bytes:
    """Inject fallback fonts into the SVG when absent."""

    try:
        svg_text = svg_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        svg_text = svg_path.read_text(encoding="utf-8", errors="ignore")

    if 'data-wechat-font-fallback="true"' in svg_text:
        return svg_text.encode("utf-8")

    style_tag = (
        '<style type="text/css" data-wechat-font-fallback="true">{}</style>'
    ).format(_build_font_fallback_css())

    if '<style' in svg_text:
        svg_text = svg_text.replace('<style', style_tag + '<style', 1)
    else:
        match = SVG_TAG_PATTERN.search(svg_text)
        if match:
            insert_pos = match.end(1)
            svg_text = svg_text[:insert_pos] + style_tag + svg_text[insert_pos:]
        else:
            svg_text = style_tag + svg_text

    return svg_text.encode("utf-8")


def convert_svg_to_jpg(svg_path: Path) -> Path:
    """Convert an SVG file to JPEG and return the new path."""

    temp_dir = Path("data/svg")
    temp_dir.mkdir(parents=True, exist_ok=True)

    jpg_name = svg_path.stem + ".jpg"
    jpg_path = temp_dir / jpg_name
    if jpg_path.exists() and jpg_path.stat().st_mtime >= svg_path.stat().st_mtime:
        return jpg_path

    svg_bytes = _load_svg_with_fallback(svg_path)
    image = pyvips.Image.new_from_buffer(svg_bytes, "", access="sequential")

    try:
        image = image.colourspace("srgb")
    except pyvips.Error:
        pass

    if image.hasalpha():
        image = image.flatten(background=[255, 255, 255])

    if image.bands == 1:
        image = image.bandjoin([image, image])

    if image.format != "uchar":
        try:
            image = image.cast("uchar")
        except pyvips.Error:
            pass

    image.write_to_file(str(jpg_path), Q=95, strip=True)

    return jpg_path


def ensure_raster_image(image_path: str) -> str:
    """Convert SVG files to JPEG for WeChat compatibility."""

    if not image_path.lower().endswith(".svg"):
        return image_path

    try:
        jpg_path = convert_svg_to_jpg(Path(image_path))
        return str(jpg_path)
    except Exception as exc:  # pragma: no cover - keep pipeline resilient
        print("convert svg error: {}".format(exc))
        return image_path


__all__ = [
    "ensure_raster_image",
    "convert_svg_to_jpg",
]
