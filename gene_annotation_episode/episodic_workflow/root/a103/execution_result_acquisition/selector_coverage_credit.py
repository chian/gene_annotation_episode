"""Credit actual retained byte-position coverage against the original selector."""
from __future__ import annotations
from .execution_contracts import math, plain

class ResultsSelectorCoverageCredit:

    def _generic_result_selector_progress(self, context, results, initial):
        """Credit saved byte positions once, regardless of read boundaries."""
        target = self._target(context)
        requested = self._windows(self._selector(plain(context.assignment), target))
        if not requested:
            return 0.0

        def covered(windows, start, end):
            intervals = sorted(((max(start, window['offset']), min(end, window['offset'] + window['returned_bytes'])) for window in windows if window['offset'] < end and window['offset'] + window['returned_bytes'] > start))
            total, right = (0, start)
            for left, stop in intervals:
                if stop > right:
                    total += stop - max(left, right)
                    right = stop
            return total
        fractions = []
        for path, (start, length) in requested.items():
            windows = [(reference, window) for reference, body in results.items() for window in body['windows'] if window['path'] == path]
            observed_end = max((window['size_bytes'] for _, window in windows), default=start)
            end = start + length if length is not None else max(start, observed_end)
            if end <= start:
                fractions.append(0.0)
                continue
            all_bytes = covered((window for _, window in windows), start, end)
            old_bytes = covered((window for reference, window in windows if reference in initial), start, end)
            fractions.append((all_bytes - old_bytes) / (end - start))
        return math.fsum(fractions) / len(fractions)

