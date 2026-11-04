"""Selected scientific images: immutable native bytes and explicit display transforms.

This module decodes a chosen frame. It neither reads biological outcomes nor
chooses another image, frame, region or scientific interpretation.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile

from PIL import Image, UnidentifiedImageError, __version__ as PILLOW_VERSION

from .domain import ContractError, canonical
from .materials import artifact_file, artifact_path

VERSION = "selected_native_image_frame_v1"


def prepare_image(store, source_ref, *, frame=0, colour_conversion="preserve"):
    source = store._require(source_ref, {"source"})
    original = artifact_path(store, source["artifact_ref"])
    try:
        with Image.open(original) as image:
            native_format, native_mode = image.format, image.mode
            frame_count = getattr(image, "n_frames", 1)
            if not 0 <= frame < frame_count:
                raise ContractError("image_frame_outside_source", detail={
                    "source_ref": source_ref, "frame": frame, "frame_count": frame_count})
            image.seek(frame)
            image.load()
            width, height = image.size
            selected = image.convert("RGB") if colour_conversion == "rgb" else image
            with tempfile.TemporaryDirectory(prefix="image-view-", dir=store.path) as temporary:
                output = Path(temporary) / "selected.png"
                try:
                    selected.save(output, format="PNG")
                except (OSError, ValueError) as error:
                    raise ContractError("image_mode_requires_explicit_conversion", detail={
                        "source_ref": source_ref, "native_mode": image.mode,
                        "colour_conversion": colour_conversion,
                        "available_conversion": "rgb"}) from error
                # Native PNG encoding can silently clamp 32-bit integer pixels.
                # Check the actual round trip rather than treating successful
                # writing as proof that an unchanged representation was made.
                with Image.open(output) as saved:
                    saved.load()
                    display_mode = saved.mode
                    if colour_conversion == "preserve":
                        restored = saved if saved.mode == selected.mode else saved.convert(selected.mode)
                        same = (hashlib.sha256(selected.tobytes()).digest()
                                == hashlib.sha256(restored.tobytes()).digest())
                        if selected.mode == "P":
                            same = same and (hashlib.sha256(selected.convert("RGBA").tobytes()).digest()
                                == hashlib.sha256(saved.convert("RGBA").tobytes()).digest())
                        if not same:
                            raise ContractError("image_pixels_not_preserved_in_png", detail={
                                "source_ref": source_ref, "native_mode": selected.mode,
                                "display_mode": display_mode,
                                "available_conversion": "rgb"})
                artifact = artifact_file(store, output, "image/png")
            return {"representation": VERSION, "input_source_ref": source_ref,
                "original_artifact_ref": source["artifact_ref"], "image_artifact_ref": artifact,
                "native_format": native_format, "native_initial_mode": native_mode,
                "selected_mode": image.mode, "display_mode": display_mode,
                "frame": frame, "frame_count": frame_count, "width": width, "height": height,
                "colour_conversion": colour_conversion, "software": "Pillow",
                "software_version": PILLOW_VERSION,
                "geometric_transform": "identity", "contrast_transform": "identity",
                "orientation": "stored_pixel_axis_no_exif_rotation"}
    except UnidentifiedImageError as error:
        raise ContractError("source_not_decodable_image", detail={"source_ref": source_ref}) from error


def view_metadata(store, view_ref):
    view = store._require(view_ref, {"image_view"})
    if view["origin"] != "tool":
        raise ContractError("native_image_view_required")
    source = store._require(view["source_ref"], {"source"})
    if source["origin"] != "tool" or source["provider"] != "image.view":
        raise ContractError("native_image_view_source_required")
    if view["representation"] != VERSION:
        raise ContractError("image_view_representation_mismatch")
    original = store._require(view["input_source_ref"], {"source"})
    if original["artifact_ref"] != view["original_artifact_ref"]:
        raise ContractError("image_original_source_mismatch")
    artifact = store._require(view["image_artifact_ref"], {"artifact"})
    if source["artifact_ref"] != artifact["id"]:
        raise ContractError("image_display_source_mismatch")
    # Artifacts identify bytes. If identical native PNG bytes were captured as
    # opaque caller material first, their original MIME label remains valid
    # custody metadata; decoding below establishes the display representation.
    return view


def visual_input(store, view_ref):
    return view_metadata(store, view_ref)


def resolve_image_input(store, selected):
    """Resolve only an actual view selection, not arbitrary paths or source JSON."""
    expected = visual_input(store, selected["id"])
    if canonical(selected) != canonical(expected):
        raise ContractError("image_input_selection_mismatch")
    path = artifact_path(store, expected["image_artifact_ref"])
    with Image.open(path) as image:
        if image.format != "PNG" or image.size != (expected["width"], expected["height"]):
            raise ContractError("image_display_dimensions_mismatch")
    return {"type": "localImage", "path": str(path.resolve())}
