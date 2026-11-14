"""Declare this terminal child original factual report fields."""
from __future__ import annotations


class HPCReportFields:
    def fact_sources(self,role):
        return {'practical_completed':{'type':'boolean','meaning':
                'Whether original requested endpoint predicates have a saved validated completion.'},
            'practical_receipt_digests':{'type':'array','meaning':
                'Host-recorded digests of the original selected command receipts.'},
            'practical_receipt_refs':{'type':'array','meaning':
                'Original selected command, actual result and earned operational credit sources.',
                'report_schema':{'type':'array','uniqueItems':True,'items':{
                    'type':'string','format':'reference','x-reference-namespace':'practical_receipt'},
                    'x-source':'practical_receipt_refs'}}}

