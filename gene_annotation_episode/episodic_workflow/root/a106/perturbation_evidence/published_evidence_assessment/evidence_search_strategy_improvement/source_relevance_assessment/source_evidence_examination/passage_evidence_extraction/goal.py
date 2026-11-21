"""What this episode is for: the extraction of one perturbation experiment's sheet from one chunk of a source's text."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/passage_evidence_extraction'
ROLE = 'literature_targeted'      # the role the library's sheet repositories read
GOAL = ('Fill the perturbation form from one chunk of a source. Extract exactly what the form asks and nothing else; a '
        'field the chunk does not state stays unavailable.')
UNIT = 'one extraction of the next chunk, with the perturbation sheet computed from what was extracted'
RESULT = ('the perturbation sheet saved from each extracted chunk, and the source as a verified lead when a sheet was '
          'saved')
