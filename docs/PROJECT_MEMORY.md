# FlightResilience Project Memory

This file records the operational rules learned from
`FlightResilience_Master_Workflow_PLAN.md`. Future work in this repository
should treat these rules as project memory.

## Hard Constraints

- Use BTS official data, or a mirror that is traceable to BTS. This repository
  uses official BTS TranStats PREZIP monthly files for 2024-01 to 2024-03.
- Preserve a full system-engineering loop: data -> system boundary -> fishbone
  and ISM -> prediction -> network -> propagation -> strategies -> evaluation
  and decision -> Web demo -> report/PPT/script.
- Do not use random train/test splits. Use chronological splits:
  train through 2024-02-15, validation through 2024-02-29, test in March 2024.
- Do not use actual operation outcomes or delay cause fields as plan-stage
  prediction features.
- Compare four recovery strategies on the same initial states, scenarios,
  horizon, cost coefficients, and resource-budget logic.
- State clearly that costs, capacity drops, and recovery resources are scenario
  parameters unless observed data supports them.
- Interpret SHAP, lag relations, ISM, and simulation as structural evidence or
  association, not strict causal identification.
- Web pages must use computed/precomputed results, not placeholder screens.
- Report, PPT, script, Demo, screenshots, and tables must use the same numbers.

## Current Frozen Scope

- Time: 2024-01-01 to 2024-03-31.
- Airports: top 15 by total BTS traffic in the selected sample.
- Key airport under the current criticality index: DEN.
- Prediction target: `ArrDel15`.
- Main decision profile: recovery/resilience priority, AHP weight share 0.90.
- Main recommended strategy: `dynamic_combo`.
- Conservative risk/cost profile can favor `baseline`; keep this as a
  sensitivity/risk-decision result rather than hiding the reversal.

## Execution Order

Run:

```powershell
python scripts/00_run_all.py
streamlit run app/Home.py
```

Then verify screenshots, report, slides, and script before submission.

