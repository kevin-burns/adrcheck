# 2. Fold rows, never drop them

Status: accepted

## Context

A report is rebuilt from repeated sweeps of the same sources.

## Problem

Rows deleted after triage return as new and the counts drift.

## Forces

Readers want a short report. Reviewers want to know what was seen before.

## Solution

Therefore, a row the pipeline decides not to show is folded, not dropped: it stays in the data the report
is built from, carries its reason, and is counted.

## Resulting Context

Every pile is listed, never hidden. Storage grows with history.
