"""Credit: one unit for each current partner sheet this Episode saved (a graded partner experiment of the examined
source). A read or a refused grading earns nothing; an assessment revision replaces its predecessor and adds nothing.
Never bounded, clamped or rescaled.

The old ``credit.py`` asked ``services.scientific_credit`` (the old shared root, not a source); the finding-progress
projector of the axis counts retained assessments, which this episode cannot write (it has no reasoning commit), so it
could never see the episode's own work. What this episode produces is graded partner sheets: they are its credit."""
SHEET_UNIT = 1.0     # one current graded partner sheet; credits are compared through settings


def credit(summary, records):
    return SHEET_UNIT * len(summary['partner_sheets'])
