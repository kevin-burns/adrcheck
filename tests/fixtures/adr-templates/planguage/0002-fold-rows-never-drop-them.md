# 2. Fold rows, never drop them

Tag: FoldNotDrop
Status: accepted
Gist: Rows the triage hides stay in the data with a reason.
Must: A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built from, carries its reason, and is counted.
Rationale: Deleted rows return as new on the next sweep and counts drift.
Assumptions: Sweeps repeat and adverts recur.
Risks: Storage grows with history.
