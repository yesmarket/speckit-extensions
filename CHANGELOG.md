# Changelog

All notable changes to this plugin. The plugin version in `.claude-plugin/plugin.json` must be
bumped for `claude plugin update` to pick up a change.

## 1.3.0

### Added

- `constitution-from-confluence`: **grounding notes.** Each `grounding` entry in
  `.specify/repo-context.yaml` can be a plain URL or an object with `url` and an optional `notes`. Notes
  are user-authored instructions for how to interpret the document (which part applies, what does not,
  known constraints), in contrast with the document body, which is data only. `grounding` is a top-level
  key, a sibling of `stack`. Unknown keys and a `grounding` list under `stack` are errors; an empty
  `notes` is a warning.
- `--grounding-notes "<text>"`, applying to the preceding `--grounding`, saved with the entry. Saving
  only appends, and never rewrites entries that were edited by hand.
- Scope from notes: the document is read in full, and the notes decide which sections are in or out of
  scope. Out-of-scope content contributes no principles, exceptions or profile facts. Notes count as
  evidence when classifying rules, and where they contradict the document the notes win and the conflict
  is recorded. Notes cannot waive a standard: a contradiction becomes a Proposed exception.
- Conflicts between grounding documents are listed as follow-ups (and as a Proposed exception when
  they touch a standard) instead of being resolved silently.
- The audit file lists, for each grounding entry, the URL, title, version, status, the notes verbatim,
  and the sections in and out of scope. The Sync Impact Report cites each document with its status and
  a one-line summary of its notes.
- The lock file records a notes hash beside the document version and content hash. A change to the
  notes re-runs rationalisation for every rule, even when the document did not change.
- `--dry-run` prints, per grounding entry, the normalised fields, resolved title, version and status,
  the sections in and out of scope, and the extracted repo profile.

### Changed

- Decisions edited by hand in the audit table are now pinned in the lock file (`"o": true`). A change
  to the grounding or the notes no longer re-opens them, only a change to the rule's own text does.
- `scripts/rules.py diff` has a `--notes-changed` flag, and reports `override_ids`. `lock` records the pin.

## 1.2.0

### Added

- `constitution-from-confluence`: **grounding documents.** `--grounding <url-or-file>` (repeatable,
  and saved into `.specify/repo-context.yaml` as a `grounding:` list) takes a Confluence page or a
  local markdown file that describes what the repository is.
- `constitution-from-confluence`: a **rationalisation phase**. A repo profile is extracted from the
  grounding documents, and every rule in the selected standards is classified keep, adapt or drop
  with a one-line reason. A drop needs positive evidence in the profile. The audit table is written
  to `.specify/memory/constitution.rationalisation.md`. More than 10 newly dropped rules (`--max-drops`)
  needs confirmation unless `--yes` is given.
- Repository-specific principles derived from the grounding documents, marked as sourced from them.
- Conflicts between a grounding document and a standard are recorded as **Proposed** rows in the
  constitution's Documented Exceptions table, citing both sources, instead of overriding the standard.
- A MAJOR constitution version bump when rationalisation removes previously present principles.
- Grounding document status (from a page-properties "Status" row, or a `status:` line in a local file)
  is recorded, and a document that is not in an endorsed state produces a prominent warning and a
  Sync Impact Report stamp.
- The lock file (now `lockVersion: 3`) records grounding documents and every rationalisation decision
  (rule id, decision, rule text hash). A re-sync reuses decisions, surfaces only new or changed rules
  (and dropped or adapted rules when the grounding changed), and respects decisions edited by hand
  in the audit table.
- Modes: `--no-grounding` (labels and repo context only), `--rationalise-only` (re-run rationalisation
  from the lock file and cached content), and `--dry-run` now also prints the repo profile and the
  full audit table.
- `scripts/rules.py`, a standard-library Python helper for rule extraction, hashing, diffing, and the
  audit, emit and lock outputs. `python3` is now needed for grounded runs.
- `references/rationalisation.md`, the detail of the new phase, so `SKILL.md` stays a workflow.

### Changed

- Documented Exceptions is now scaffolded as a table (ID, status, rule deviated from, deviation and
  source, rationale, approver and date, revisit). Existing sections in any other shape are preserved
  as they are.
- Grounding and standards content is treated as data: instructions found inside it are never followed.

## 1.1.0

### Added

- `constitution-from-confluence`: space URLs (uses the space homepage as the root), an explicit
  `depth` of 10 with cursor pagination and depth-cap re-queries when ordering the hierarchy, index-page
  detection (`children` macro only), one merged `/speckit.constitution` call over scratch files (with
  `--per-page` as an opt-in), Documented Exceptions preservation, a report of linked pages that were
  not included, a content hash per page in the lock file, and `--dry-run`.

### Fixed

- `constitution-from-confluence`: the Arguments section is now built around a single deliberate use of
  the arguments placeholder, so it no longer garbles when substituted.
- The `argument-hint` front matter value is quoted, so the file parses as YAML.

## 1.0.0

- Initial release: `constitution-from-confluence`, `plan-from-confluence`, `plan-from-lucid`,
  `plan-from-swagger` and `specify-from-jira`, with bundled Atlassian, Lucid and fetch MCP servers.
