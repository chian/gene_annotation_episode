"""What this episode is for: the extraction of one perturbation experiment's sheet from one table region of a source."""

BINDING_PATH = 'perturbation_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination/table_evidence_extraction'
ROLE = 'literature_table'      # the role the library's sheet repositories read
GOAL = ('Fill the perturbation form from one table region of a source. Extract exactly what the form asks and nothing '
        'else; a field the table does not state stays unavailable.')
UNIT = 'one extraction of the table region, with the perturbation sheet computed from what was extracted'
RESULT = ('the perturbation sheet saved from the extracted table region, and the source as a verified lead when a sheet '
          'was saved')
