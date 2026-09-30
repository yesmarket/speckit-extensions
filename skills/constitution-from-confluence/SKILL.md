---
name: constitution-from-confluence
description: Use when the user wants to generate or refresh a project constitution from the Delivery Standards in Confluence — e.g. "constitution from confluence", "refresh the constitution", "/speckit-extensions:constitution-from-confluence". Reads .specify/repo-context.yaml, selects the steering-labelled pages under Delivery Standards whose appliesto-* labels match the repo's stack, feeds each into /speckit.constitution, and records what was used in .specify/memory/constitution.lock.yaml.
user-invocable: true
argument-hint: [confluence-url] [--force] [additional-input]
---

# constitution-from-confluence

Build (or refresh) a repository's speckit constitution from the delivery standards published in Confluence. Only the pages relevant to this repository's stack are used.

The same command handles both first-time generation and later refreshes. It detects which by looking for the lock file.

## Defaults

| Setting | Default |
|---|---|
| Confluence site | `humm-group.atlassian.net` |
| Space | `DDS` (Design and Delivery Standards) |
| Root page | `Delivery Standards`, page ID `5818974222` |
| Repo context file | `./.specify/repo-context.yaml` |
| Lock file | `./.specify/memory/constitution.lock.yaml` |

All paths are relative to the root of the repository being worked on (the current working directory).

## Arguments

`$ARGUMENTS` contains: `[confluence-url] [--force] [additional-input]`

- `confluence-url` (optional): URL of a Confluence page to use as the root instead of `Delivery Standards`, e.g. `https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Page+Title`. Only pages beneath this root are considered.
- `--force` (optional): regenerate even when nothing has changed since the lock file was written.
- `additional-input` (optional): extra context or instructions, passed as a separate final invocation of `/speckit.constitution`.

## Which pages are included

A page is included when **both** are true:

1. It has the label `steering`.
2. It has **no** `appliesto-*` labels (universal), **or** at least one of its `appliesto-*` labels matches the repo context.

Pages without `steering` are never included, whatever else they carry.

### Applicability labels

Format: `appliesto-<namespace>-<value>`, lower case. The namespace is the first segment after the prefix and the value is everything after it (values may contain hyphens).

| Label namespace | Repo context key | Example label | Matches when `stack` has |
|---|---|---|---|
| `lang` | `languages` | `appliesto-lang-java` | `languages: [java]` |
| `cloud` | `cloud` | `appliesto-cloud-aws` | `cloud: [aws]` |
| `platform` | `platforms` | `appliesto-platform-ansible` | `platforms: [ansible]` |
| `domain` | `domains` | `appliesto-domain-broker-portal` | `domains: [broker-portal]` |

Matching rules:

- Comparison is case-insensitive after trimming whitespace.
- A page with several `appliesto-*` labels is included if **any one** of them matches (OR, never AND).
- The prefix `applies-to-` is accepted as an alias for `appliesto-`.
- A label that starts with the prefix but has an unknown namespace or an empty value is malformed. Warn about it, ignore it for matching, and still treat the page as restricted. A malformed label must never turn a page into a universal one. If all of a page's applicability labels are malformed, exclude the page and say so.

Examples, with the repo context `languages: [java]`, `cloud: [aws]`, `platforms: []`, `domains: []`:

| Page labels | Included? | Why |
|---|---|---|
| `steering` | Yes | Universal |
| `steering`, `appliesto-lang-java` | Yes | `java` matches |
| `steering`, `appliesto-lang-dotnet` | No | No match |
| `steering`, `appliesto-platform-ansible`, `appliesto-cloud-aws` | Yes | `aws` matches (OR) |
| `appliesto-lang-java` | No | Not labelled `steering` |

With `platforms: [ansible, terraform]` instead, `steering` + `appliesto-platform-ansible` is included.

## Steps

**IMPORTANT: Only perform read operations against Confluence. Never create, edit, or delete pages, comments, labels, or any other Confluence resources. The only files this skill writes are the lock file and whatever `/speckit.constitution` writes.**

### 1. Parse Arguments

Consume leading tokens of `$ARGUMENTS` while each is either a URL (starts with `http://` or `https://`) or `--force`. Everything after that is `additional-input`.

### 2. Read the Repo Context

Read `./.specify/repo-context.yaml`. It declares the repository's stack:

```yaml
stack:
  languages: [java]
  cloud: [aws]
  platforms: [ansible, terraform]
  domains: []
```

- Each of `languages`, `cloud`, `platforms`, `domains` is a list of strings. A missing key or `[]` means empty. A single string is treated as a one-element list.
- Lower-case and trim every value.
- If the file is **missing, unreadable, or has no `stack` key**, do not stop. Fall back to the empty stack, so that only universal pages (no `appliesto-*` labels) are included. Warn the user clearly, say the result will be a thinner constitution, and show the example above so they can create the file.
- Warn about (but ignore) unknown keys under `stack`.

### 3. Resolve the Root Page

Use the defaults above, unless a `confluence-url` was given. In that case take the site host from the URL and the `pageId` from the path segment after `/pages/` (`https://<domain>/wiki/spaces/<spaceKey>/pages/<pageId>/<title>`).

### 4. Discover Candidate Pages

Using the Atlassian MCP server, run one CQL search (the `searchConfluenceUsingCql` tool) with the site as `cloudId`:

```
ancestor = <rootPageId> AND type = page AND label = "steering"
```

Request `expand` = `content.metadata.labels,content.version` so each result carries its full label set and its version number. `ancestor` covers every descendant at any depth, but not the root itself. Use `limit` 100 and keep paging until `totalSize` results have been collected.

The search response is large because it includes author and history data for every hit. If it is saved to a file rather than returned inline, extract only what is needed with a shell tool (for example a short `python3` or `jq` command) instead of reading the whole file. For each result keep:

- `content.id`
- `content.title`
- `content.version.number`
- the names in `content.metadata.labels.results[*].name`

### 5. Filter by Labels

Apply "Which pages are included" to each candidate using the repo context from step 2. For every candidate record whether it is **included** and why: `universal`, or `matched: <namespace>-<value>` naming the first matching label. Record excluded candidates too, with a short reason (`no matching appliesto label`, `malformed label`).

If no pages are included, stop and tell the user. Do not invoke `/speckit.constitution` and do not touch the lock file.

### 6. Order the Included Pages

Order pages by their position in the hierarchy, depth-first, parent before its children, siblings in their Confluence order. Fetch the tree once with the `getConfluencePageDescendants` tool for the root page (large `depth`, following pagination) and use `parentId`, `depth` and `childPosition` to sort. If that call fails, order by title.

### 7. Compare with the Lock File

Read `./.specify/memory/constitution.lock.yaml`.

- **No lock file**: this is a first-time generation. Continue to step 8.
- **Lock file exists**, and its `source.rootPageId` matches the root in use: compare the included pages against the lock's `pages` list, by page ID, and report:
  - **Added**: included now, absent from the lock.
  - **Removed**: in the lock, no longer included (deleted, unlabelled, moved out of the hierarchy, or no longer matching the repo context).
  - **Updated**: same page, different `version`.
  - **Unchanged**: same page, same `version`.
  - Also note if the `repoContext` recorded in the lock differs from the current one.
- **Lock file exists for a different root**: warn, then treat as a first-time generation.

If a lock file exists, nothing was added, removed or updated, the repo context is unchanged, and `--force` was not given, report "constitution is up to date with Confluence", print the unchanged page list, and stop. Do not invoke `/speckit.constitution` and do not rewrite the lock file.

### 8. Fetch the Page Content

For each included page, fetch the full body with the `getConfluencePage` tool, requesting `markdown` (fall back to `html` if markdown is rejected). On a refresh, fetch every included page, not just the changed ones, so the constitution is regenerated from the whole set.

### 9. Feed Each Page into /speckit.constitution

**On a refresh only**, make one first invocation of `/speckit.constitution` with a sync-context block, so the constitution can drop guidance that no longer applies:

```
Sync context: the constitution is being refreshed from Confluence.
Added pages: <titles, or none>
Updated pages: <titles, or none>
Removed pages (guidance from these should no longer apply unless another page below repeats it): <titles, or none>
The full set of currently applicable pages follows, one per invocation.
```

Then, for each included page in order, invoke `/speckit.constitution` once with this context block:

```
Confluence Page: <pageId>
Space: <spaceKey>
Title: <page title>
Version: <version number>
Labels: <comma-separated label set>
URL: <page URL or canonical link>

Content:
<full page body>
```

Do not batch multiple pages into a single invocation. Each page must be a separate call. Treat the normative keywords in the content (**MUST**, **SHOULD**, **MAY**) as load-bearing and preserve them.

### 10. Pass Additional Input (if provided)

If `additional-input` was supplied, make one final invocation of `/speckit.constitution` with that content as the context. This is a separate call from the per-page invocations above.

### 11. Write the Lock File

Only after the invocations above have completed, write `./.specify/memory/constitution.lock.yaml` (create the directory if needed). It is machine-written; the pattern is the same as `package-lock.json`. Commit it alongside the constitution.

```yaml
# Written by constitution-from-confluence. Do not edit by hand.
generatedAt: 2026-09-30T03:30:00Z
source:
  site: humm-group.atlassian.net
  space: DDS
  rootPageId: "5818974222"
  rootTitle: Delivery Standards
repoContext:
  languages: [java]
  cloud: [aws]
  platforms: []
  domains: []
pages:
  - id: "5884313654"
    title: Engineering Principles
    version: 8
    labels: [steering]
    reason: universal
  - id: "5887000591"
    title: Java Standards
    version: 10
    labels: [steering, appliesto-lang-java]
    reason: "matched: lang-java"
skipped:
  - id: "5886017558"
    title: .NET Standards
    labels: [steering, appliesto-lang-dotnet]
    reason: no matching appliesto label
```

`pages` lists the included pages in the order they were fed in. `skipped` lists steering pages that were excluded, so it is easy to see why a page is missing. Use the current UTC time for `generatedAt`.

### 12. Report

Finish with a short summary:

- First-time generation or refresh, and the root used.
- The repo context used (say so if the fallback was applied).
- Pages included, with the reason for each, and pages skipped, with the reason.
- On a refresh: what was added, removed and updated.
- Any warnings (missing repo context, malformed labels).
- That the lock file was written, and that it should be committed together with `.specify/memory/constitution.md`.
