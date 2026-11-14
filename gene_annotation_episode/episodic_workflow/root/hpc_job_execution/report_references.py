"""Authenticate original terminal receipt references."""
from __future__ import annotations
from ..terminal_execution import digest

class HPCReportReferences:
    def resolve(self,context,reference,namespace):
        if self.store is not None and isinstance(reference,str) and reference.startswith('source_'):
            from ..practical_receipt_information import PracticalReceiptInformation
            return PracticalReceiptInformation(self.store,context.run_id).resolve(context,reference,namespace)
        return namespace=='practical_receipt' and reference in {digest(row) for row in self.state(context).receipts()}

