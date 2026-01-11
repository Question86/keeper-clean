# REPORT: TASK_0027 - Token Usage Estimator (Auto + Quick Adjust)

**REPORT ID:** report_TASK_0027_L15_v01.md  
**LOOP:** 15  
**TASK:** TASK_0027  
**DATE:** 2026-01-10  
**STATUS:** ✅ SUCCESS

---

## SOURCE REFERENCE

[ref:task_TASK_0027.md|v:1|tags:task|src:user]

---

## OBJECTIVE

Make the token usage estimator practical without requiring manual guessing/typing, while still allowing manual override.

---

## IMPLEMENTATION

### Auto (Time-Based) Estimator Mode
- Added an **AUTO** mode that estimates token usage as a function of elapsed time.
- AUTO mode stores:
  - `tokenEstimateAutoBase` (baseline token count)
  - `tokenEstimateAutoStartMs` (anchor timestamp)
  - `tokenEstimateAutoRatePerMin` (configurable rate)
- AUTO mode can be enabled/paused; pausing converts the current computed value into the manual stored estimate.

### Quick-Adjust Controls
- Added one-click adjustment buttons to reduce friction:
  - `-5K`, `+5K`, `+10K`, `+25K`, `+50K`
- Adjustments work in both modes:
  - MANUAL: updates stored manual estimate.
  - AUTO: adjusts the auto baseline (so the auto curve shifts without resetting time).

### Persistence and Safety
- Continued using localStorage persistence for the displayed estimate.
- Added range clamping to keep values within `0..1,000,000`.
- Added a small mode label for visibility: `Mode: MANUAL` or `Mode: AUTO (~rate/min)`.

---

## FILES CHANGED

- templates/cockpit.html

---

## ACCEPTANCE CRITERIA STATUS

- [x] No longer requires manual token guessing as the only workflow (AUTO mode available)
- [x] Fast interaction for corrections (quick-adjust buttons)
- [x] Persistence across reloads (localStorage)
- [x] Manual override remains possible

---

END OF REPORT
