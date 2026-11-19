"""What this episode is for: the A105 examination of one exact source, carried from the old ``goal.py``
(``SourceGoal.instructions``: the role instruction of ``literature_page`` in ``source_contracts._ROLE_INSTRUCTIONS``
and the shared investigation paragraph) at 97308b94c. The planning question of ``SourceGoal.planning_context`` is
``PLANNING_QUESTION``; ``task.py`` and ``messages/internal_summary.py`` show it to the model."""

BINDING_PATH = 'experimental_activity_evidence/published_evidence_assessment/evidence_search_strategy_improvement/source_relevance_assessment/source_evidence_examination'
GOAL = ('Investigate where and how this exact source should be examined. Choose ordinary source operations or '
        'selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit '
        'some XML headings, tables and footnotes; retained original bytes remain addressable.\n'
        'This is an iterative scientific investigation in the shared Episode loop. Earlier outcomes and admitted '
        'child forms inform later choices; no child order, reading quota or complete-document requirement is '
        'prescribed. A one-off search/read is an ordinary tool. A supplied reading selector is context, not an '
        "automatically executed action. Preserve the source's actual subject, experimental conditions, "
        'representation, version and UTF-8 byte anchors. Distinguish source claims from their applicability to the '
        'fixed target. Negative findings and qualifications can advance the investigation. Commit interpretations '
        "with the common reasoning action and update only the parent's declared typed form in that same work call. "
        'Navigation, byte coverage and repeated reading earn no scientific credit by themselves. The commissioned '
        "task's own yield settings guide continuation.")
UNIT = ('one model-selected unit on the assigned source: a catalog lookup, an access tool, a population sheet, a '
        'reasoning commit coupled with its grading sheets, the report tool, or one commission of a table, '
        'ordered-reading or targeted-passage investigation')
RESULT = ('the typed investigation finding of the examination of the assigned source for the assigned question (the '
          "actual source claim, source subject and qualification), with the commissioned task's typed answers "
          '(screening answers, source-lead dispositions, quantity, assay-grading and aggregation cells) the parent '
          'selects')
PLANNING_QUESTION = ('Which unresolved part of the commissioned source assessment should be investigated next, using '
                     'the actual findings and returned components? Choose source operations or one of the declared '
                     'children; revise the approach from outcomes while preserving the original objective.')
