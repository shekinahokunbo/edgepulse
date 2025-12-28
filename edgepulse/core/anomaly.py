def _median(xs):
    xs = sorted(xs)
    return xs[len(xs) // 2]

def robust_zscore(errors, eps=1e-3):
    m = _median(errors)
    devs = [abs(e - m) for e in errors]
    mad = _median(devs)

    # Scale floor: at least eps, and also at least 10% of typical error magnitude
    scale_floor = max(eps, 0.1 * abs(m) + eps)
    mad = max(mad, scale_floor)

    return (errors[-1] - m) / (1.4826 * mad)

def is_anomaly(errors, z_thresh=3.5, min_points=20):
    if len(errors) < min_points:
        return False, 0.0
    z = robust_zscore(errors)
    return abs(z) >= z_thresh, z
