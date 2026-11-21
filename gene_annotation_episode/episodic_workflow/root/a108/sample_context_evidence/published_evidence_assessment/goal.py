"""What this episode is for: which published evidence bears on the commissioned A108 organism-context question. It is
the top of the literature chain and does what the top of nano-graphrag's chain does: it proposes the next search
strategy and hands it down. It runs no search, fetches no paper and reads no paper text; the search below it obtains a
paper when its page is built, and what the page and its leaves find is graded there automatically. Nothing in this
episode is assessed by a reasoning commit.

Carried from the old ``goal.py`` (``LiteratureGoal.instructions``) of ``literature`` at 97308b94c, with the ordinary
searches, source reads, reasoning commit and the three task kinds other than the verified source leads removed."""

BINDING_PATH = 'sample_context_evidence/published_evidence_assessment'
ROLE_INSTRUCTION = (
    "Investigate which published evidence bears on whether the proposed protein function fits the actual organism's "
    "biology and sample conditions: physiology (what the organism is observed to do), environment (habitat, "
    "temperature, pH, oxygen, growth conditions), availability (the relevant substrates and cofactors) and "
    "localization (whether the protein and the required molecules can occur in compatible cellular locations). The "
    "supplied organism, strain and sample context is a job operand, not evidence; the question context records name "
    "it. You do not search for papers, fetch them or read them. Commission the search strategy investigation with "
    "its objective; it proposes the searches, a search level runs each one and picks a paper, a page level examines "
    "that paper, and what is found in it is graded automatically where it is found. Choose the next objective from "
    "what the strategy returned (its credit and the features of its findings). The configured controller alone "
    "decides when this episode stops.")
GOAL = ROLE_INSTRUCTION
UNIT = ('one model-selected read of the records this episode holds, or one child commission (the strategy '
        'investigation of which searches are productive for the question)')
RESULT = ('the controlled features code reads from the A108 subscoring and main evidence sheets saved (the '
          "children's), with the sheet and graded assessment references, and the verified source leads as counts "
          'and references')
