"""What this episode is for: the extraction of perturbation experiment sheets from the windows of a source read in document
order, window after window."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/source_coverage_improvement'
ROLE = 'literature_ordered'      # the role the library's sheet repositories read
GOAL = ('Fill the perturbation form from each window of a source read in document order. Extract exactly what the form '
        'asks and nothing else; a field a window does not state stays unavailable.')
UNIT = 'one extraction of the next window, with the perturbation sheet computed from what was extracted'
RESULT = ('the perturbation sheet saved from each extracted window, and the source as a verified lead when a sheet was '
          'saved')
