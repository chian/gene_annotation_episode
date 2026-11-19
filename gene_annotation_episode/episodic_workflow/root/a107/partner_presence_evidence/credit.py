"""Credit: the finding unit the commissioner named for each distinct component of the A107 scoring sheet this Episode
holds: each literature partner sheet its children returned (each sheet once), each native component record and each
per-use tool qualification record. The three groups are counted side by side, never combined into a score; a search, a
read or a commission earns nothing by itself. Never bounded, clamped or rescaled. A parent's credit is its own
measurement of what it holds, not a sum of its children's credits.

The old credit view was ``services.scientific_credit`` (old runner) over the axis's finding progress, which counts
retained assessments; the A107 evidence this Episode receives is graded sheets and component records, which that
projection never sees (and which reads the Store through ``read_snapshot``, a transaction the reader does not offer)."""


def credit(summary, records):
    received = summary['received']
    count = (len(summary['literature_sheets']) + len(received['native_components'])
             + len(received['qualifications']))
    return summary['finding_unit'] * count
