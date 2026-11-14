"""Private A110 decision-exchange instruction text."""
INSTRUCTIONS = """
Your internal decision may take several model exchanges. Return the required
closed response object. Use response_type=request_context to request your own
prior attempts through the declared lookup form. This only retrieves information
you already received; it does not perform new scientific work or complete an
action. After its decision_lookup_result arrives, continue the SAME decision.
Use request_context for own attempt metadata and selected inputs. Its
own_attempt_detail pointer addresses selected inputs, not their outputs. Use
the ordinary episode.history tool with view=records and selected
decision_indices to read exact previously received outcomes together. That
read is an ordinary action with its own completion observation; it does not
execute the historical actions or earn their old credit again. The reader
cannot access another episode's private history.
Use response_type=select_action with selection and report_update when ready to
dispatch an actual action. Only that action's actual completion supplies an
observation to your configured continuation controller.

decision_bootstrap supplies an authoritative scoped model state. decision_update
replaces the listed top-level fields and removes exactly removed_fields; omitted
fields keep their previous values. base_revision identifies the previous state
and revision identifies the resulting state. Newer state replaces older values,
including yield expectations; older estimates remain historical. A bootstrap
after conversation loss or compaction replaces earlier presentation state.
decision_lookup_result supplies only the requested own historical information.
Restored public exchanges preserve the requests and results of an unfinished
decision; do not repeat their already answered lookups merely to restore memory.

action_yields describes your OWN completed action categories. total_yield is
observed signed gain, excluding inherited credit. Expected category yield is
conditional on choosing and completing that category again; unavailable is not
zero. Approximate model bands are not calibrated next-outcome guarantees. Useful
evidence acquisition can have zero immediate credit when a later interpretation
earns the credit. Failed or unexecuted attempts have no completed-action gain.
Use recorded inputs and result references to distinguish specific prior attempts.
""".strip()

# Text-rendered scientific decisions preserve this protocol's action/lookup and
# yield meanings. Frame identities remain host reconstruction details, so the
# provider uses this variant only for published investigation instructions.
_FRAME_INSTRUCTIONS = INSTRUCTIONS[INSTRUCTIONS.index('decision_bootstrap supplies'):
    INSTRUCTIONS.index('action_yields describes')]
TEXT_INSTRUCTIONS = INSTRUCTIONS.replace(_FRAME_INSTRUCTIONS,
    'Each request supplies the complete task and current decision-relevant information. '
    'Current values replace earlier values, including yield expectations; prior estimates '
    'remain historical. A requested own-history lookup continues this same pending decision. '
    'Previously answered lookups remain answered after reconstruction; do not repeat them '
    'merely to restore memory.\n\n')

