import pandas as pd
from vitrina.datasets.services import get_period_key, bucket_grouped_rows


def test_period_key_matches_filter_fields():
    label = pd.Period("2023-01-03", freq="D")
    assert get_period_key("D", "created", label) == (2023, 1, 3)
    assert get_period_key("Y", "created", pd.Period("2023", freq="Y")) == (2023,)
    wk = pd.Period("2022-12-28", freq="W")
    assert get_period_key("W", "created", wk) == (wk.year, wk.month, wk.week)


def test_bucket_grouped_rows_none_to_zero():
    rows = [
        {"created__year": 2023, "count": None},
        {"created__year": 2022, "count": 5},
    ]
    buckets = bucket_grouped_rows(rows, "Y", "created")
    assert buckets[(2023,)] == 0
    assert buckets[(2022,)] == 5


def test_bucket_grouped_rows_sums_rows_with_same_period():
    rows = [
        {"created__year": 2022, "count": 2},
        {"created__year": 2022, "count": 3},
        {"created__year": 2023, "count": 1},
    ]
    buckets = bucket_grouped_rows(rows, "Y", "created")
    assert buckets[(2022,)] == 5
    assert buckets[(2023,)] == 1
