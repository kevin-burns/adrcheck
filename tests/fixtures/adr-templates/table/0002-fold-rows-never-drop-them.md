# 2. Fold rows, never drop them

| Field | Value |
|---|---|
| Status | accepted |
| Context | Rows deleted after triage return as new on the next sweep and the counts drift. |
| Options | Drop rows the triage says no to. Keep a separate archive table. |
| Decision | A row the pipeline decides not to show is folded, not dropped: it stays in the data the report is built from, carries its reason, and is counted. |
| Consequences | Every pile is listed, never hidden. Storage grows with history. |
