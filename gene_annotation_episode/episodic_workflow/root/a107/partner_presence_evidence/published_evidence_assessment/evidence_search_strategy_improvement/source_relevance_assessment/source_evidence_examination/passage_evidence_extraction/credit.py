"""Credit: the finding unit the parent commissioned for each current partner sheet this Episode saved (a graded
partner experiment of the examined source). A read or a refused grading earns nothing; an assessment revision
replaces its predecessor and adds nothing. Never bounded, clamped or rescaled.

The old ``credit.py`` asked ``services.scientific_credit`` (the old shared root, not a source); the finding-progress
projector of the axis counts retained assessments, which this leaf cannot write (it has no reasoning commit), so it
could never see the leaf's own work. What this leaf produces is graded partner sheets: they are its credit."""
def credit(summary, records):
    return summary['finding_unit'] * len(summary['partner_sheets'])
