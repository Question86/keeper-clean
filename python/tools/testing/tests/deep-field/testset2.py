import json, os, time, random, math, re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Tuple, Optional

RESULTS_PATH = "/mnt/data/comprehensive_test_results.json"
STABLE_PATH = "/mnt/data/stable_regions_analysis.json"

with open(RESULTS_PATH, "r") as f:
    RESULTS = json.load(f)
with open(STABLE_PATH, "r") as f:
    STABLE = json.load(f)

@dataclass
class Event:
    component: str                 # e.g., "axiom2.timescale"
    kind: str                      # "REINFORCEMENT" | "NEAR_MISS" | "CONTRADICTION"
    severity: float                # 0..1
    detail: Dict[str, Any]

def classify_timescale(test: Dict[str, Any], stable: Dict[str, Any]) -> Event:
    ratio = float(test["ratio"])
    max_safe = float(stable.get("max_safe_ratio", 0.1))
    # strict: contradiction if failed; else near-miss if within 5% of max_safe
    if not test["passed"]:
        return Event("axiom2.timescale", "CONTRADICTION", 1.0, {"ratio": ratio, "max_safe_ratio": max_safe, "reason": test.get("error")})
    near = ratio >= 0.95 * max_safe
    return Event("axiom2.timescale", "NEAR_MISS" if near else "REINFORCEMENT",
                 0.6 if near else 0.2,
                 {"ratio": ratio, "max_safe_ratio": max_safe})

def classify_contraction(test: Dict[str, Any], stable: Dict[str, Any]) -> Event:
    sr = float(test["spectral_radius"])
    c_max = float(test["c_max"])
    max_stable_sr = float(stable.get("max_stable_spectral_radius", 0.8))
    if not test["passed"]:
        # severity grows with how far beyond c_max (or beyond 1.0 if present)
        overflow = max(0.0, sr - c_max)
        sev = min(1.0, 0.7 + 0.6 * overflow)
        return Event("axiom3.contraction", "CONTRADICTION", sev, {"spectral_radius": sr, "c_max": c_max, "max_stable_spectral_radius": max_stable_sr, "reason": test.get("error")})
    near = sr >= 0.95 * min(c_max, 1.0)
    return Event("axiom3.contraction", "NEAR_MISS" if near else "REINFORCEMENT",
                 0.7 if near else 0.25,
                 {"spectral_radius": sr, "c_max": c_max, "max_stable_spectral_radius": max_stable_sr})

def classify_mi(test: Dict[str, Any], stable: Dict[str, Any], snr_max: float = 1e6) -> Event:
    snr = float(test["snr"])
    min_noise = float(stable.get("min_safe_noise", 1e-12))
    if not test["passed"]:
        return Event("axiom4.noise_guard", "CONTRADICTION", 0.9, {"snr": snr, "snr_max": snr_max, "min_safe_noise": min_noise, "reason": test.get("error")})
    near = snr >= 0.95 * snr_max
    # MI guard is weak evidence when passing; treat as low-severity reinforcement
    return Event("axiom4.noise_guard", "NEAR_MISS" if near else "REINFORCEMENT",
                 0.4 if near else 0.1,
                 {"snr": snr, "snr_max": snr_max, "min_safe_noise": min_noise, "noise_std": test.get("noise_std"), "z_magnitude": test.get("z_magnitude")})

def events_from_json(results: Dict[str, Any], stable: Dict[str, Any]) -> List[Event]:
    evs: List[Event] = []
    for t in results.get("timescale_separation", []):
        evs.append(classify_timescale(t, stable.get("timescale_separation", {})))
    for t in results.get("contraction_stability", []):
        evs.append(classify_contraction(t, stable.get("contraction_stability", {})))
    for t in results.get("mi_finiteness", []):
        evs.append(classify_mi(t, stable.get("mi_finiteness", {})))
    return evs

EVS = events_from_json(RESULTS, STABLE)
len(EVS), EVS[:3]

