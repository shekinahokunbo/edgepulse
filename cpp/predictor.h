#pragma once

extern "C" {
// Predict next value using EWMA + short-term trend.
// window: array of doubles (oldest -> newest), length n
// alpha: smoothing (0..1)
double predict_next(const double* window, int n, double alpha);
}
