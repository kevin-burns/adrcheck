# 2. Fold rows, never drop them

Status: accepted

In the context of a report built from repeated sweeps, facing rows that return as new after being deleted,
we decided for rows that are folded, not dropped, and kept in the data with a reason and neglected the
alternative, Drop rows the triage says no to, to achieve stable counts across sweeps, accepting that storage grows with
history.
