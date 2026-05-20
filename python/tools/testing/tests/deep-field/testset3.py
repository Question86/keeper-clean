@dataclass
class AnchorState:
    anchor_id: str
    confidence: float
    age_steps: int
    contradiction_exposure: float
    replacement_cost: float
    lineage: str

def clamp01(x): 
    return max(0.0, min(1.0, float(x)))

def apply_event(a: AnchorState, e: Event) -> AnchorState:
    # deterministic, conservative updates
    # global aging + decay (even on reinforcement)
    age = a.age_steps + 1
    # base decay proportional to age pressure
    conf = a.confidence * (0.999)  # tiny decay per event
    contr = a.contradiction_exposure * (0.999)  # tiny relaxation over time (very slow)

    if e.kind == "REINFORCEMENT":
        conf += 0.015 * (1.0 - conf) * (1.0 - e.severity)  # bounded
        contr -= 0.010 * contr  # small reduction
    elif e.kind == "NEAR_MISS":
        conf -= 0.010 * e.severity
        contr += 0.020 * e.severity * (1.0 - contr)
    else:  # CONTRADICTION
        conf -= 0.050 * e.severity
        contr += 0.120 * e.severity * (1.0 - contr)

    return AnchorState(
        anchor_id=a.anchor_id,
        confidence=clamp01(conf),
        age_steps=age,
        contradiction_exposure=clamp01(contr),
        replacement_cost=clamp01(a.replacement_cost),  # only changes when dependencies change (not in this event stream)
        lineage=a.lineage
    )

def reanchor_if_needed(a: AnchorState, contradiction_thr=0.85, replace_cost_thr=0.80) -> Tuple[AnchorState, bool]:
    if a.contradiction_exposure >= contradiction_thr and a.replacement_cost < replace_cost_thr:
        # re-anchor: new lineage, reset confidence/contradiction; keep replacement cost
        new_lineage = a.lineage + "->R"
        return AnchorState(
            anchor_id=a.anchor_id,
            confidence=0.35,
            age_steps=0,
            contradiction_exposure=0.15,
            replacement_cost=a.replacement_cost,
            lineage=new_lineage
        ), True
    return a, False

# Initialize anchors for components
anchors = {
    "axiom2.timescale": AnchorState("axiom2.timescale", 0.55, 0, 0.10, 0.70, "v0"),
    "axiom3.contraction": AnchorState("axiom3.contraction", 0.55, 0, 0.10, 0.65, "v0"),
    "axiom4.noise_guard": AnchorState("axiom4.noise_guard", 0.55, 0, 0.10, 0.55, "v0"),
}

# Run long-horizon accumulation over the existing events as a demo
reanchors = 0
for e in EVS:
    a = anchors[e.component]
    a = apply_event(a, e)
    a, did = reanchor_if_needed(a)
    reanchors += int(did)
    anchors[e.component] = a

anchors, reanchors

