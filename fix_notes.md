# Fix Notes

## Selected fix

1. Adam's P2 lost-update report against `POST /api/links` and `GET /u/<code>`.

Why this fix: the report shows ordinary valid requests receiving success responses while their
created links are silently lost from the JSON store. That directly violates P2 correctness and
also affects hit counters through the same read-modify-write pattern.

Plan: make link creation and hit-counter updates serialize the complete load/mutate/save
transaction, then add regression coverage for concurrent creates and concurrent follows.

## Issue lookup

`gh issue list --label valid --limit 20` could not run in this workspace because `gh` is not
installed, so this triage is based on the Adam report provided in chat.
