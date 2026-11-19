"""Gel experimental guidance, separate from numerical contracts and readers."""


GEL_OPERATION_DESCRIPTION = (
    "Quantify explicitly selected lane, band, background and whole-lane regions from received original "
    "8-bit grayscale PNG/JPEG images. Preserve source-backed experimental/lane meanings, unknowns and "
    "conflicts. The v1 definition uses mean background; v2 requires each lane's explicit mean or median "
    "choice. Populate exact raw pixel summaries, background-corrected darkness, lane display fractions, "
    "competition contrasts and available-only sensitivity across nominated coherent ROI alternatives. "
    "Negative corrected signals remain negative; a direct contrast can survive an unavailable baseline. "
    "No OCR, image classification or graph-axis extraction is performed. Image darkness is not calibrated "
    "molecular occupancy; ROI-choice ranges are not sampling confidence intervals, and dependent "
    "representations are not independent experiments. No target transfer or annotation credit is calculated.")

__all__ = ['GEL_OPERATION_DESCRIPTION']
