"""Very short trend data of the measured durations of one kind of job, read from the estimate ledger.

The ledger is the estimate table (``episode_runtime/estimate_table.py``): one file that outlasts every run. A job
that is launched leaves one row: what was expected of it before it ran (``expected``) and, once it has ended, what
happened (``actual``). The row's ``expected`` carries the facts of the job that were known before it ran, under
``job`` (``{name: value}``: the service, the program, the database, the size of the query and so on); its ``actual``
carries ``duration_seconds`` and ``outcome``.

``duration_trend`` turns the rows of one kind into what an estimate is made from, in a few numbers:

- how many jobs of the kind were measured, and their 10th percentile, median and 90th percentile;
- the latest measured durations, newest first (a service that has become slower shows here before the median moves);
- once enough jobs of different sizes are measured, a straight line fitted through duration against one size field
  of the job (least squares: ``seconds = seconds_at_zero + seconds_per_unit * size``), with the duration it gives
  for the size asked about and how far the measured durations lie from the line (the median distance in seconds:
  a line whose distance is as large as the spread of the durations says the size explains little).

Only jobs that ended as ``finished`` are measured durations; a job that failed or is still open is counted beside
them and enters no number. Nothing here reads a file: the caller hands in the rows (``EstimateTable.rows(kind)``)."""
import math

FINISHED = 'finished'


def _quantile(values, fraction):
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    low = math.floor(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _line(points):
    """The least-squares line through ``points`` (``[(size, seconds)]``): ``(seconds_at_zero, seconds_per_unit)``."""
    count = len(points)
    mean_size = math.fsum(size for size, _ in points) / count
    mean_seconds = math.fsum(seconds for _, seconds in points) / count
    spread = math.fsum((size - mean_size) ** 2 for size, _ in points)
    slope = math.fsum((size - mean_size) * (seconds - mean_seconds) for size, seconds in points) / spread
    return mean_seconds - slope * mean_size, slope


def duration_trend(rows, *, size_field=None, size=None, latest=5, fit_minimum=5):
    """The trend of the measured durations among ``rows`` (the ledger's rows of one kind, latest first).

    ``size_field`` names the field of a row's ``expected['job']`` that measures the size of the job and ``size`` the
    size asked about. The line is fitted when at least ``fit_minimum`` measured jobs carry the field and they have at
    least two different sizes; otherwise ``size_fit`` is ``None``."""
    measured = [row for row in rows if row['actual'] is not None and row['actual']['outcome'] == FINISHED
                and 'duration_seconds' in row['actual']]
    durations = [row['actual']['duration_seconds'] for row in measured]
    trend = {'measured': len(measured),
             'not_finished': sum(1 for row in rows if row['actual'] is not None
                                 and row['actual']['outcome'] != FINISHED),
             'open': sum(1 for row in rows if row['actual'] is None),
             'low_seconds': _quantile(durations, 0.1) if durations else None,
             'typical_seconds': _quantile(durations, 0.5) if durations else None,
             'high_seconds': _quantile(durations, 0.9) if durations else None,
             'latest_seconds': durations[:latest], 'size_fit': None}
    if size_field is not None:
        points = [(row['expected']['job'][size_field], row['actual']['duration_seconds']) for row in measured
                  if size_field in row['expected'].get('job', {})]
        if len(points) >= fit_minimum and len({point[0] for point in points}) >= 2:
            at_zero, per_unit = _line(points)
            trend['size_fit'] = {'size_field': size_field, 'points': len(points), 'seconds_at_zero': at_zero,
                                 'seconds_per_unit': per_unit,
                                 'typical_distance_seconds': _quantile(
                                     [abs(seconds - at_zero - per_unit * size_) for size_, seconds in points], 0.5),
                                 'predicted_seconds': None if size is None else at_zero + per_unit * size}
    return trend


__all__ = ['FINISHED', 'duration_trend']
