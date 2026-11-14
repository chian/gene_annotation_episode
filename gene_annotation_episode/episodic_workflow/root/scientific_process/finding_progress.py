"""Original scientific finding-progress definition selected by this process."""
def finding_progress():
    from ..investigation_progress import FindingProgressPolicy, ScientificFindingProgress
    return ScientificFindingProgress(FindingProgressPolicy(finding_unit=1))


