#include "predictor.h"

extern "C" double predict_next(const double* window, int n, double alpha) {
    if (!window || n <= 0) return 0.0;
    if (n == 1) return window[0];

    // EWMA "level"
    double level = window[0];
    for (int i = 1; i < n; i++) {
        level = alpha * window[i] + (1.0 - alpha) * level;
    }

    // Trend from last few points
    int k = (n < 6) ? n : 6;
    double trend = 0.0;
    for (int i = n - k + 1; i < n; i++) {
        trend += (window[i] - window[i - 1]);
    }
    trend /= (k - 1);

    return level + trend;
}
