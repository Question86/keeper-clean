# Create a markdown report template + log, and write an executable runner script to /mnt/data
report_path = "/mnt/data/report_anchor_field_demo.md"
runner_path = "/mnt/data/anchor_event_pipeline.py"

anchor_field = {k: asdict(v) for k,v in anchors.items()}
header = {"anchor_field": anchor_field, "generated_from": ["comprehensive_test_results.json","stable_regions_analysis.json"]}

md = []
md.append("<!--ANCHOR_FIELD\n" + json.dumps(header, indent=2) + "\nANCHOR_FIELD-->")
md.append("\n# Anchor Field Report (Demo)\n")
md.append("This report is a *stateful* anchor snapshot plus an append-only event log.\n")
md.append("## Current Anchor States\n")
for k,v in anchors.items():
    md.append(f"- **{k}**: confidence={v.confidence:.3f}, age_steps={v.age_steps}, contradiction_exposure={v.contradiction_exposure:.3f}, replacement_cost={v.replacement_cost:.2f}, lineage={v.lineage}\n")
md.append("\n## Event Log (Append-only)\n")
for i,e in enumerate(EVS, start=1):
    md.append(f"{i:04d}. {e.component} | {e.kind} | severity={e.severity:.2f} | detail={e.detail}\n")

with open(report_path,"w") as f:
    f.write("\n".join(md))

# Write the runner script (standalone)
script = f'''\
"""
anchor_event_pipeline.py

Deterministic pipeline:
- Load your test-result JSON batches (comprehensive_test_results.json + stable_regions_analysis.json)
- Classify each test outcome into events: REINFORCEMENT / NEAR_MISS / CONTRADICTION
- Update an anchor field (CACR) deterministically
- Write a markdown report with a JSON header + append-only log

This is NOT a theorem verifier. It is an experience accumulator.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Tuple

RESULTS_PATH = r"{RESULTS_PATH}"
STABLE_PATH  = r"{STABLE_PATH}"
OUT_REPORT   = r"{report_path}"

@dataclass
class Event:
    component: str
    kind: str
    severity: float
    detail: Dict[str, Any]

@dataclass
class AnchorState:
    anchor_id: str
    confidence: float
    age_steps: int
    contradiction_exposure: float
    replacement_cost: float
    lineage: str

def clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))

def classify_timescale(test: Dict[str, Any], stable: Dict[str, Any]) -> Event:
    ratio = float(test["ratio"])
    max_safe = float(stable.get("max_safe_ratio", 0.1))
    if not test["passed"]:
        return Event("axiom2.timescale", "CONTRADICTION", 1.0, {{"ratio": ratio, "max_safe_ratio": max_safe, "reason": test.get("error")}})
    near = ratio >= 0.95 * max_safe
    return Event("axiom2.timescale", "NEAR_MISS" if near else "REINFORCEMENT", 0.6 if near else 0.2, {{"ratio": ratio, "max_safe_ratio": max_safe}})

def classify_contraction(test: Dict[str, Any], stable: Dict[str, Any]) -> Event:
    sr = float(test["spectral_radius"])
    c_max = float(test["c_max"])
    max_stable_sr = float(stable.get("max_stable_spectral_radius", 0.8))
    if not test["passed"]:
        overflow = max(0.0, sr - c_max)
        sev = min(1.0, 0.7 + 0.6 * overflow)
        return Event("axiom3.contraction", "CONTRADICTION", sev, {{"spectral_radius": sr, "c_max": c_max, "max_stable_spectral_radius": max_stable_sr, "reason": test.get("error")}})
    near = sr >= 0.95 * min(c_max, 1.0)
    return Event("axiom3.contraction", "NEAR_MISS" if near else "REINFORCEMENT", 0.7 if near else 0.25, {{"spectral_radius": sr, "c_max": c_max, "max_stable_spectral_radius": max_stable_sr}})

def classify_mi(test: Dict[str, Any], stable: Dict[str, Any], snr_max: float = 1e6) -> Event:
    snr = float(test["snr"])
    min_noise = float(stable.get("min_safe_noise", 1e-12))
    if not test["passed"]:
        return Event("axiom4.noise_guard", "CONTRADICTION", 0.9, {{"snr": snr, "snr_max": snr_max, "min_safe_noise": min_noise, "reason": test.get("error")}})
    near = snr >= 0.95 * snr_max
    return Event("axiom4.noise_guard", "NEAR_MISS" if near else "REINFORCEMENT", 0.4 if near else 0.1, {{"snr": snr, "snr_max": snr_max, "min_safe_noise": min_noise, "noise_std": test.get("noise_std"), "z_magnitude": test.get("z_magnitude")}})

def events_from_json(results: Dict[str, Any], stable: Dict[str, Any]) -> List[Event]:
    evs: List[Event] = []
    for t in results.get("timescale_separation", []):
        evs.append(classify_timescale(t, stable.get("timescale_separation", {{}})))
    for t in results.get("contraction_stability", []):
        evs.append(classify_contraction(t, stable.get("contraction_stability", {{}})))
    for t in results.get("mi_finiteness", []):
        evs.append(classify_mi(t, stable.get("mi_finiteness", {{}})))
    return evs

def apply_event(a: AnchorState, e: Event) -> AnchorState:
    age = a.age_steps + 1
    conf = a.confidence * 0.999
    contr = a.contradiction_exposure * 0.999

    if e.kind == "REINFORCEMENT":
        conf += 0.015 * (1.0 - conf) * (1.0 - e.severity)
        contr -= 0.010 * contr
    elif e.kind == "NEAR_MISS":
        conf -= 0.010 * e.severity
        contr += 0.020 * e.severity * (1.0 - contr)
    else:
        conf -= 0.050 * e.severity
        contr += 0.120 * e.severity * (1.0 - contr)

    return AnchorState(a.anchor_id, clamp01(conf), age, clamp01(contr), clamp01(a.replacement_cost), a.lineage)

def reanchor_if_needed(a: AnchorState, contradiction_thr=0.85, replace_cost_thr=0.80) -> Tuple[AnchorState, bool]:
    if a.contradiction_exposure >= contradiction_thr and a.replacement_cost < replace_cost_thr:
        return AnchorState(a.anchor_id, 0.35, 0, 0.15, a.replacement_cost, a.lineage + "->R"), True
    return a, False

def main() -> None:
    with open(RESULTS_PATH, "r") as f:
        results = json.load(f)
    with open(STABLE_PATH, "r") as f:
        stable = json.load(f)

    events = events_from_json(results, stable)

    anchors: Dict[str, AnchorState] = {{
        "axiom2.timescale": AnchorState("axiom2.timescale", 0.55, 0, 0.10, 0.70, "v0"),
        "axiom3.contraction": AnchorState("axiom3.contraction", 0.55, 0, 0.10, 0.65, "v0"),
        "axiom4.noise_guard": AnchorState("axiom4.noise_guard", 0.55, 0, 0.10, 0.55, "v0"),
    }}

    reanchors = 0
    for e in events:
        a = anchors[e.component]
        a = apply_event(a, e)
        a, did = reanchor_if_needed(a)
        reanchors += int(did)
        anchors[e.component] = a

    header = {{
        "anchor_field": {{k: asdict(v) for k,v in anchors.items()}},
        "generated_from": ["comprehensive_test_results.json","stable_regions_analysis.json"],
        "reanchors": reanchors
    }}

    lines = []
    lines.append("<!--ANCHOR_FIELD\\n" + json.dumps(header, indent=2) + "\\nANCHOR_FIELD-->")
    lines.append("\\n# Anchor Field Report\\n")
    lines.append("This file is a stateful anchor snapshot plus an append-only event log.\\n")
    lines.append("## Current Anchor States\\n")
    for k,v in anchors.items():
        lines.append(f"- **{{k}}**: confidence={{v.confidence:.3f}}, age_steps={{v.age_steps}}, contradiction_exposure={{v.contradiction_exposure:.3f}}, replacement_cost={{v.replacement_cost:.2f}}, lineage={{v.lineage}}\\n")
    lines.append("\\n## Event Log (Append-only)\\n")
    for i,e in enumerate(events, start=1):
        lines.append(f"{{i:04d}}. {{e.component}} | {{e.kind}} | severity={{e.severity:.2f}} | detail={{e.detail}}\\n")

    with open(OUT_REPORT, "w") as f:
        f.write("".join(lines))

if __name__ == "__main__":
    main()
'''
with open(runner_path,"w") as f:
    f.write(script)

report_path, runner_path

