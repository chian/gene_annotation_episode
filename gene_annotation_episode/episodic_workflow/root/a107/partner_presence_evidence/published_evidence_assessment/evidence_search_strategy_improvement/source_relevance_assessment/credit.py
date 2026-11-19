"""Credit: the finding unit the parent commissioned for each distinct partner sheet this episode holds (its own current
sheets and those its children returned, each sheet once). A read, a refused grading or a child that saved nothing earns
nothing. Never bounded, clamped or rescaled. A parent's credit is its own measurement of what it holds, not a sum of
its children's credits.

The old credit view was ``services.scientific_credit`` (old runner); the axis's finding-progress projector counts
retained assessments, which no A107 literature episode writes. What these episodes produce is graded partner sheets:
they are the credit."""


def credit(summary, records):
    return summary['finding_unit'] * len(summary['partner_sheets'])
