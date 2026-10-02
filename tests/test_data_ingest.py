"""Calendar alignment and validation run offline on small fixtures (no network)."""
import numpy as np
import pandas as pd
import pytest

from src.data_ingest import align_calendar, apply_demergers, validate_prices

DATES = pd.date_range("2026-01-01", periods=4, freq="D")


def test_align_drops_dates_missing_any_series():
    prices = pd.DataFrame({"STOCK": [100, 101, 102, 103],
                           "^NSEI": [np.nan, 200, np.nan, 202]}, index=DATES, dtype=float)
    aligned, dropped = align_calendar(prices)
    assert aligned.index.tolist() == [DATES[1], DATES[3]]
    assert dropped == ["2026-01-01", "2026-01-03"]


def test_demerger_removes_spun_off_value_from_ex_date_return():
    # Cum close 100, Rs 10 of value spun off, stock opens ex at 90: no real loss.
    prices = pd.DataFrame({"A": [98, 100, 90, 91], "B": [50, 51, 52, 53]},
                          index=DATES, dtype=float)
    adj = apply_demergers(prices, [{"ticker": "A", "ex_date": "2026-01-03",
                                    "spun_off_value": 10, "cum_close": 100}])
    assert adj["A"].tolist() == pytest.approx([88.2, 90, 90, 91])
    assert adj["A"].pct_change().iloc[2] == pytest.approx(0.0)
    assert adj["B"].equals(prices["B"])        # other tickers untouched
    assert prices.at[DATES[0], "A"] == 98      # input not mutated


def test_validate_passes_clean_prices():
    prices = pd.DataFrame({"A": [100, 101, 99, 100]}, index=DATES, dtype=float)
    validate_prices(prices, max_abs_move=0.20)


def test_validate_flags_large_move():
    prices = pd.DataFrame({"A": [100, 101, 70, 71]}, index=DATES, dtype=float)
    with pytest.raises(ValueError, match="A:2026-01-03"):
        validate_prices(prices, max_abs_move=0.20)


def test_validate_accepts_whitelisted_move():
    prices = pd.DataFrame({"A": [100, 101, 70, 71]}, index=DATES, dtype=float)
    validate_prices(prices, max_abs_move=0.20, allowed=["A:2026-01-03"])


@pytest.mark.parametrize("bad", [
    pd.DataFrame({"A": [100, np.nan, 99, 100]}, index=DATES),
    pd.DataFrame({"A": [100, 0, 99, 100]}, index=DATES, dtype=float),
    pd.DataFrame({"A": [100, 101, 99, 100]}, index=DATES[::-1], dtype=float),
])
def test_validate_rejects_unusable_tables(bad):
    with pytest.raises(ValueError):
        validate_prices(bad, max_abs_move=0.20)
