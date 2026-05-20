from performance_benchmark import RegressionDetector


def test_regression_detector_detects_change():
    rd = RegressionDetector(thresholds={'benchmarks.bootstrap.duration_seconds': 0.10})
    baseline = {'benchmarks': {'bootstrap': {'duration_seconds': 1.0}}}
    current = {'benchmarks': {'bootstrap': {'duration_seconds': 1.3}}}

    regressions = rd.check_regression(baseline, current)
    assert len(regressions) == 1
    assert regressions[0]['metric'] == 'benchmarks.bootstrap.duration_seconds'
    assert regressions[0]['severity'] in ('MEDIUM', 'HIGH')
