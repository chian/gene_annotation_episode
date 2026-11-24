"""Credit: the commissioned task's credit, ``credit_unit`` for the verified source of the original question (the old
``LiteratureTaskCredit`` rule for ``verified_source_leads``: one unit per verified source; revision, activity and repeated
reading earn nothing). The leaf has one source. It is verified when a chunk of it has been extracted and the population
route saved the perturbation sheet: the route authenticated every quotation of the sheet against the source's bytes
(``lead_source_refs``, ``messages/internal_summary.py``). Never bounded, clamped or rescaled here."""


def credit(summary, records):
    return summary['task']['credit_unit'] * len(summary['lead_source_refs'])


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` is the next unit: the leaf has one source, so an ``extract`` can add
    at most the unit not yet earned, whatever its arguments (``credit_unit`` less the credit, no less than 0); any other
    action type is not offered and cannot earn: 0."""
    if action_type != 'extract':
        return 0.0
    return max(0.0, summary['task']['credit_unit'] - credit(summary, records))
