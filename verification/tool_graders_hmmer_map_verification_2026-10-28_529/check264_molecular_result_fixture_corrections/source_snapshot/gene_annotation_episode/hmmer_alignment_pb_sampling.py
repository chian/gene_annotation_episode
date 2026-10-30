"""Pure row-ordinal sampling for retained Easel PB reconstruction.

This ports MT19937-64 and the Vitter D/A implementation in
``resources/software/infernal-1.1.5/easel/esl_rand64.c``. The native generator
derives from Makoto Matsumoto and Takuji Nishimura's MT19937-64; Easel's Deal
implementation derives from Kevin Lawler's Vitter implementation.

The caller supplies the effective PB seed. This module neither infers that
seed from CLI options nor decides whether an alignment should be sampled. It
returns calculated zero-based source-row ordinals, not observed native output.
PB counts, weights, fragment handling and occurrence joins belong to the common
alignment reconstruction. Floating calculations retain the source operation
order; native equivalence still depends on the platform's double/libm behavior.
"""
from __future__ import annotations

import math


_UINT64_MAX = (1 << 64) - 1
_INT64_MAX = (1 << 63) - 1

__all__ = ["sample_easel_pb_rows"]


class _EaselMT19937_64:
    """The retained generator's uint64 stream and two needed double forms."""

    def __init__(self, seed: int) -> None:
        self._mt = [0] * 312
        self._mt[0] = seed
        for z in range(1, 312):
            previous = self._mt[z - 1]
            self._mt[z] = (
                6364136223846793005 * (previous ^ (previous >> 62)) + z
            ) & _UINT64_MAX
        self._fill_table()

    def _fill_table(self) -> None:
        mt = self._mt
        mag01 = (0, 0xB5026F5AA96619E9)
        for z in range(156):
            x = (mt[z] & 0xFFFFFFFF80000000) | (mt[z + 1] & 0x7FFFFFFF)
            mt[z] = mt[z + 156] ^ (x >> 1) ^ mag01[x & 1]
        for z in range(156, 311):
            x = (mt[z] & 0xFFFFFFFF80000000) | (mt[z + 1] & 0x7FFFFFFF)
            mt[z] = mt[z - 156] ^ (x >> 1) ^ mag01[x & 1]
        x = (mt[311] & 0xFFFFFFFF80000000) | (mt[0] & 0x7FFFFFFF)
        mt[311] = mt[155] ^ (x >> 1) ^ mag01[x & 1]
        self._mti = 0

    def uint64(self) -> int:
        if self._mti >= 312:
            self._fill_table()
        x = self._mt[self._mti]
        self._mti += 1
        x ^= (x >> 29) & 0x5555555555555555
        x ^= (x << 17) & 0x71D67FFFEDA60000
        x ^= (x << 37) & 0xFFF7EEE000000000
        x ^= x >> 43
        return x

    def double(self) -> float:
        return float(self.uint64() >> 11) * (1.0 / 9007199254740992.0)

    def double_open(self) -> float:
        return (float(self.uint64() >> 12) + 0.5) * (1.0 / 4503599627370496.0)


def _log(value: float) -> float:
    # C log(0) produces -infinity; Python's math.log(0) raises ValueError.
    # The initial [0,1) draw can be zero. Subsequent draws are in (0,1).
    return -math.inf if value == 0.0 else math.log(value)


def _round_nonnegative(value: float) -> float:
    """C round() on the nonnegative domain used by vitter_a()."""
    fraction, integer = math.modf(value)
    return integer + 1.0 if fraction >= 0.5 else integer


def _vitter_a(
    rng: _EaselMT19937_64, m: int, n: int, j: int, deal: list[int]
) -> None:
    top = float(n - m)
    nreal = float(n)
    while m >= 2:
        u = rng.double_open()
        skip = 0
        quotient = top / nreal
        while quotient > u:
            skip += 1
            top -= 1.0
            nreal -= 1.0
            quotient = (quotient * top) / nreal
        j += skip + 1
        deal.append(j)
        nreal -= 1.0
        m -= 1
    skip = math.floor(_round_nonnegative(nreal) * rng.double())
    j += skip + 1
    deal.append(j)


def _validate_settings(population_size: int, sample_size: int, seed: int) -> None:
    if (
        type(population_size) is not int
        or type(sample_size) is not int
        or type(seed) is not int
        or not 1 <= sample_size <= population_size <= _INT64_MAX
        or sample_size > _INT64_MAX // 13
        or not 1 <= seed <= _UINT64_MAX
    ):
        raise ValueError("settings_invalid")


def sample_easel_pb_rows(
    population_size: int, *, sample_size: int, seed: int
) -> list[int]:
    """Return Easel's sorted sample without replacement from ``range(N)``.

    All three arguments must be built-in integers, excluding booleans. Native
    ``n`` and ``m`` are signed int64; this port requires ``1 <= m <= n`` and
    ``m <= INT64_MAX // 13`` because native setup calculates ``13*m``. The seed
    must be in ``1..UINT64_MAX``. These are native definition bounds, not a
    resource policy. Invalid settings raise ``ValueError('settings_invalid')``.

    Native ``m=0`` still writes one element and does not implement an empty
    sample. Native seed zero chooses time-dependent state, which cannot be
    reconstructed from this port's inputs. Both are rejected explicitly.
    """
    _validate_settings(population_size, sample_size, seed)
    rng = _EaselMT19937_64(seed)
    m = sample_size
    n = population_size
    j = -1
    qu1 = n - m + 1
    threshold = 13 * m
    mreal = float(m)
    nreal = float(n)
    minv = 1.0 / float(m)
    # This draw occurs even if the very first branch is Method A or m == 1.
    vprime = math.exp(minv * _log(rng.double()))
    qu1real = nreal - mreal + 1.0
    deal: list[int] = []

    # The native unused setup 1.0/(m-1) may be infinity for m == 1. Its first
    # used value is computed here, where m > 1; do not raise on that setup.
    while m > 1 and n > threshold:
        mmin1inv = 1.0 / (-1.0 + mreal)
        while True:
            while True:
                x = nreal * (-vprime + 1.0)
                skip = math.floor(x)
                if skip < qu1:
                    break
                vprime = math.exp(minv * _log(rng.double_open()))
            u = rng.double_open()
            neg_skip_real = float(-skip)
            y1 = math.exp(mmin1inv * _log(u * nreal / qu1real))
            vprime = y1 * (-x / nreal + 1.0) * (
                qu1real / (neg_skip_real + qu1real)
            )
            if vprime <= 1.0:
                break

            y2 = 1.0
            top = nreal - 1.0
            if n - 1 > skip:
                bottom = nreal - mreal
                limit = n - skip
            else:
                bottom = nreal + neg_skip_real - 1.0
                limit = qu1
            for _ in range(n - 1, limit - 1, -1):
                y2 = (y2 * top) / bottom
                top -= 1.0
                bottom -= 1.0
            if nreal / (nreal - x) >= y1 * math.exp(mmin1inv * _log(y2)):
                vprime = math.exp(mmin1inv * _log(rng.double_open()))
                break
            vprime = math.exp(minv * _log(rng.double_open()))

        j += skip + 1
        deal.append(j)
        n = n - skip - 1
        nreal = nreal + neg_skip_real - 1.0
        m -= 1
        mreal -= 1.0
        minv = mmin1inv
        qu1 -= skip
        qu1real += neg_skip_real
        threshold -= 13

    if m > 1:
        _vitter_a(rng, m, n, j, deal)
    else:
        skip = math.floor(n * vprime)
        j += skip + 1
        deal.append(j)
    return deal
