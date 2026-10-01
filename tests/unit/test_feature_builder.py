"""
Unit tests for Feature Builder (features/builder.py).
Tests 22-dimensional feature vector generation, CleanBuffer operations, and warm-up edge cases.
"""
import numpy as np
from datetime import datetime, timezone, timedelta
from features.builder import (
    CleanBuffer,
    FeatureBuilder,
    feature_builder,
    build_feature_vector,
    FEATURE_DIM,
    FEATURE_VERSION,
)


def test_clean_buffer_push_and_limit():
    buf = CleanBuffer(max_size=5)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    for i in range(10):
        buf.push(20.0 + i, 1013.0, 50.0, t0 + timedelta(minutes=5 * i))

    assert len(buf) == 5
    assert buf.t_buf[-1] == 29.0
    assert buf.last_valid(buf.t_buf) == 29.0


def test_clean_buffer_with_nones():
    buf = CleanBuffer(max_size=5)
    t0 = datetime(2026, 9, 30, 0, 0, 0, tzinfo=timezone.utc)
    buf.push(20.0, 1013.0, 50.0, t0)
    buf.push(None, 1013.0, 50.0, t0 + timedelta(minutes=5))
    buf.push(22.0, 1013.0, 50.0, t0 + timedelta(minutes=10))

    assert buf.last_valid(buf.t_buf) == 22.0
    arr = buf.as_array(buf.t_buf)
    assert np.isnan(arr[1])
    assert arr[0] == 20.0


def test_build_feature_vector_dimensions_and_types():
    buf = CleanBuffer(max_size=20)
    t0 = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)

    # Push 5 historical points at 5-minute intervals
    for i in range(5):
        buf.push(20.0 + i * 0.1, 1013.0 - i * 0.05, 50.0 + i * 0.2, t0 + timedelta(minutes=5 * i))

    obs_ts = t0 + timedelta(minutes=25)
    fv = feature_builder.build(20.6, 1012.7, 51.2, obs_ts, buf)

    assert isinstance(fv, np.ndarray)
    assert fv.shape == (FEATURE_DIM,)
    assert fv.dtype == np.float32

    # Verify slot 0, 1, 2 raw values
    assert np.isclose(fv[0], 20.6)
    assert np.isclose(fv[1], 1012.7)
    assert np.isclose(fv[2], 51.2)

    # Verify first derivatives (per minute)
    # (20.6 - 20.4) / 5 min = 0.04 deg C / min
    assert np.isclose(fv[3], (20.6 - 20.4) / 5.0, atol=1e-3)

    # Verify cyclical encodings (slots 15-18)
    assert not np.isnan(fv[15])
    assert not np.isnan(fv[16])
    assert not np.isnan(fv[17])
    assert not np.isnan(fv[18])

    # Verify derived thermodynamic features (slots 19-21: dewpoint, vp, depression)
    assert not np.isnan(fv[19])  # dewpoint
    assert not np.isnan(fv[20])  # vp
    assert not np.isnan(fv[21])  # depression
    assert fv[21] > 0            # T > Td for 51.2% RH
