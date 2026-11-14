"""Gel experimental guidance, separate from numerical contracts and readers."""

GEL_TASK = """Examine what the assigned gel experiment establishes about the studied molecule. Identify the organism, construct, experimental system and measured species, and establish each lane's actual composition and conditions. Distinguish the intended change from other differences and identify the controls relevant to the requested inference.

Use the original figure and its Methods and legend to identify the relevant bands, lane regions and background. Record ambiguous bands and unavailable details. If numerical tables or raw measurements are available, extract and summarize them using the appropriate readers and calculations. Preserve negative background-corrected signals and distinguish displayed image intensity from calibrated molecular amounts.

For binding and competition, establish which labeled and unlabeled species were tested, their concentrations and whether the competitor has the same or a different sequence. Distinguish displacement, sequence specificity and attribution to the intended molecule. Identify which complementary measurements address unresolved alternatives.

Keep repeated displays, alternative region choices, multiple bands and independent preparations distinct. Use readers and calculators for the requested numerical components; return their scientific meanings, uncertainty, dependence and limitations through the parent's typed form."""

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

__all__ = ["GEL_TASK", "GEL_OPERATION_DESCRIPTION"]
