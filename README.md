# speckit-extensions

A Claude Code plugin for AI-assisted spec-driven development. Provides skills that gather context from external systems such as Jira, Confluence, Figma, and others, and pipes it into [speckit](https://github.com/github/spec-kit) commands to drive spec driven development workflows.

## Installation

**1. Add the marketplace**

```sh
claude plugin marketplace add yesmarket/claude-marketplace
```

This adds the [yesmarket/claude-marketplace](https://github.com/yesmarket/claude-marketplace) as a source for plugin installation.

**2. Install the plugin**

```sh
claude plugin install speckit-extensions@yesmarket/claude-marketplace
```

This plugin bundles the following MCP servers directly — no separate dependency installation required:

- [Atlassian Rovo hosted MCP server](https://mcp.atlassian.com)
- [Lucid MCP server](https://mcp.lucid.app/mcp)

> **Why bundle MCP servers directly?** At the time of writing, Claude Code does not auto-install plugin dependencies, so declaring an Atlassian plugin dependency would require users to install it manually. Bundling the MCP server directly keeps installation to a single step. If plugin dependency auto-installation is supported in a future release, this plugin may switch to declaring dependencies instead.
>
> **Note:** If you also have the official [Atlassian plugin](https://github.com/atlassian/atlassian-mcp-server) installed, there are no conflicts. Claude Code handles duplicate MCP server registrations gracefully.

## Skills

### `constitution-from-confluence`

Builds or refreshes a repository's speckit constitution from the delivery standards in the Design and Delivery Standards (`DDS`) Confluence space. It reads the repo's stack from `.specify/repo-context.yaml`, selects only the pages that apply to that stack, and merges them into the constitution in a single `/speckit.constitution` pass. Optionally, it grounds the constitution in a design document and rationalises the standards against it.

```
/speckit-extensions:constitution-from-confluence [confluence-url] [--grounding <url-or-file> [--grounding-notes "<text>"]]... [--dry-run] [--no-grounding] [--rationalise-only] [--yes] [--max-drops N] [--force] [--per-page] [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `confluence-url` | No | Root to use instead of `Delivery Standards` (`https://humm-group.atlassian.net/wiki/spaces/DDS/pages/5818974222`). A page URL (`.../pages/<id>/...`) uses that page. A space URL (`.../spaces/DDS/`) uses the space's homepage, so the whole space is in scope. Only pages beneath the root are considered. |
| `--grounding <url-or-file>` | No | A grounding document: a Confluence page URL or a local markdown file. Repeatable. Saved into `.specify/repo-context.yaml` so later runs reuse it. |
| `--grounding-notes "<text>"` | No | Notes for the immediately preceding `--grounding`, telling the skill how to read that document (which part applies, what does not). Quote it. Saved with the entry |
| `--dry-run` | No | Print the pages selected and skipped, the repo profile and the full audit table, without writing anything |
| `--no-grounding` | No | Ignore grounding documents (including those in the repo context). Use the standards as selected by labels and repo context only |
| `--rationalise-only` | No | Re-run rationalisation against the existing lock file and grounding, without re-discovering pages |
| `--yes` | No | Do not ask for confirmation when many rules are dropped |
| `--max-drops N` | No | Ask for confirmation when more than N rules are newly dropped (default 10) |
| `--force` | No | Regenerate even if nothing has changed since the lock file was written |
| `--per-page` | No | One `/speckit.constitution` call per page instead of one merged call. Slower and costlier; opt-in only |
| `additional-input` | No | Extra context or instructions passed as a final, separate invocation of `/speckit.constitution` |

**Example:**

```
/speckit-extensions:constitution-from-confluence
/speckit-extensions:constitution-from-confluence --dry-run
/speckit-extensions:constitution-from-confluence https://humm-group.atlassian.net/wiki/spaces/DDS/
/speckit-extensions:constitution-from-confluence https://humm-group.atlassian.net/wiki/spaces/DDS/ --grounding https://humm-group.atlassian.net/wiki/spaces/ADVE/pages/5132386339/Infrastructure-as-Code+IaC+Standards
/speckit-extensions:constitution-from-confluence https://humm-group.atlassian.net/wiki/spaces/DDS/ --grounding https://humm-group.atlassian.net/wiki/spaces/ADVE/pages/6250496035/Servicing+Comms+Template+Change+Process+-+Options+Analysis --grounding-notes "Only Option 3 applies. Options 1 and 2 are rejected alternatives. No runtime services, APIs or containers."
/speckit-extensions:constitution-from-confluence --force focus on the payments domain
```

#### Repo context

Create `.specify/repo-context.yaml` in the repository to declare its stack, and optionally its grounding documents:

```yaml
stack:
  languages: [java]
  cloud: [aws]
  platforms: [ansible, terraform]
  domains: []
grounding:
  # plain form
  - https://humm-group.atlassian.net/wiki/spaces/ADVE/pages/5132386339/Infrastructure-as-Code+IaC+Standards

  # object form, with notes
  - url: https://humm-group.atlassian.net/wiki/spaces/ADVE/pages/6250496035/Servicing+Comms+Template+Change+Process+-+Options+Analysis
    notes: >
      Only Option 3 (Automated Comms Pipeline) applies to this repo. Options 1 and 2 are
      rejected alternatives and must not contribute principles. The repo holds templates,
      Ansible roles, Terraform and a preview script; it has no runtime services, APIs or
      containers.
```

`grounding` is a top-level key, a sibling of `stack` (not nested in it, because the `stack` keys map to `appliesto-*` label namespaces). Each entry is a plain URL string or an object with exactly `url` (a Confluence page URL or a local markdown path) and an optional `notes`. Both forms can be mixed. An unknown key, or a `grounding` list under `stack`, is an error; an empty `notes` is a warning.

If the file is missing or has no `stack`, only universal pages are used (and the skill warns you), which gives a thinner but still valid constitution.

#### Which pages are used

The skill finds every page beneath the root and includes a page when it has the `steering` label and either:

- has no `appliesto-*` labels (universal, always included), or
- has at least one `appliesto-<namespace>-<value>` label that matches the repo context.

| Label namespace | Repo context key | Example label |
|---|---|---|
| `lang` | `languages` | `appliesto-lang-java` |
| `cloud` | `cloud` | `appliesto-cloud-aws` |
| `platform` | `platforms` | `appliesto-platform-ansible` |
| `domain` | `domains` | `appliesto-domain-broker-portal` |

Multiple `appliesto-*` labels on a page are OR-ed, so one match is enough. Matching is case-insensitive, and the documented `applies-to:cloud:aws` form is accepted as an alias. Pages without `steering` are never used, which keeps process pages and design-time guardrails out.

Parent pages whose body is only a "Child pages" macro are detected as index pages and skipped (their children are still considered on their own). The run reports how many pages were skipped as index or empty pages.

#### Grounding and rationalisation

The DDS standards are written for every Humm repo, and labels only say what *stack* a repo has. A grounding document (a design, options analysis or similar) says what the repo *is*, for example "templates, Ansible roles and Terraform, with no runtime services". With one, the skill adds a rationalisation phase between assembling the pages and writing the constitution:

1. **Repo profile.** It extracts a short profile from the grounding documents: what the repo contains and does not contain, its environments, approval model, secrets handling and mandatory requirements.
2. **Classify every rule.** Each numbered rule (and each unnumbered section) in the selected standards is marked **keep**, **adapt** or **drop**, with a one-line reason tied to the profile. A drop needs positive evidence in the profile: a grounding document being silent about a rule is not a reason to drop it. Kept rules keep their exact MUST/SHOULD/MAY wording and their rule numbers.
3. **Audit trail.** The full table (rule, source page, decision, reason) is written to `.specify/memory/constitution.rationalisation.md`, and a summary is printed. If more than 10 rules are newly dropped (`--max-drops`), you are asked to confirm before anything is written, unless you pass `--yes`.
4. **Repo-specific principles.** Requirements that exist only in the grounding document (for example a legal sign-off gate, or the repo being the source of truth) are added as principles marked as sourced from the grounding document, not from the standards.
5. **Conflicts are proposed exceptions.** If the grounding document conflicts with a standard (a different approver, fewer environments), the standard is not overridden. A **Proposed** row citing both sources is added to the constitution's Documented Exceptions table, and listed as a follow-up needing FAF endorsement.
6. **Compact constitution.** Related rules are consolidated into one principle, citing all their rule numbers. If rationalisation removes principles that were previously present, the constitution's version bump is MAJOR.

If a grounding document's status (from a "Status" row in its page-properties table, or a `status:` line in a local file) is not an endorsed state (`endorsed`, `approved`, `accepted`, `ratified`, `final` or `current`), the skill warns prominently and stamps the constitution's Sync Impact Report as provisional. Confluence's native page status is not readable through the Atlassian MCP tool, so only the properties-table status is checked.

#### Notes

Notes are the one place where you steer how a grounding document is read. They are **user-authored instructions**, in contrast with the document's own content, which is data only.

- **Scope.** The skill reads the whole document and uses the notes to decide which sections are in scope. If the notes say only Option 3 applies, the other options are out of scope and contribute no principles, exceptions or profile facts. `--dry-run` shows, per grounding entry, the sections treated as in scope and out of scope, so you can correct the notes.
- **Interpretation.** Notes guide the keep/adapt/drop decisions. A statement about the repo in the notes (for example "no runtime services") counts as evidence for a drop. Where the notes contradict the document's content, the notes win and the conflict is recorded in the audit file.
- **Not a waiver.** Notes cannot waive a standard. If they contradict one, the standard's rule is kept and a Proposed exception is added, citing the notes, for FAF endorsement.
- **Several documents.** If grounding documents disagree, the skill does not pick one silently. It lists the conflict as a follow-up and, where it touches a standard, adds a Proposed exception citing both documents.
- **Audit.** The audit file lists, for each grounding entry, the URL, title, version, status, the notes verbatim, and the sections in and out of scope. The Sync Impact Report cites each document with its status (for example "ADVE 6250496035, status IN PROGRESS") and a one-line summary of its notes.
- **Re-sync.** The lock file records a hash of the notes next to the document's version and content hash. Editing the notes re-runs rationalisation for every rule, even if the document did not change, except decisions you edited by hand in the audit table (those stay pinned).
- **Safety.** Only notes from `repo-context.yaml` (or `--grounding-notes` on the command line, which is saved there) are instructions. Text inside a grounding document is never followed as an instruction, however it is phrased. Notes cannot relax the skill's guardrails.
- **Command line.** `--grounding-notes` applies to the nearest `--grounding` before it and is saved with the entry. Saving only appends: existing entries you hand-edited are never rewritten, and comments and ordering are preserved.

Grounding content and the standards themselves are treated as data: the skill extracts facts from them and never follows instructions found inside them.

#### How the pages are merged

The skill writes each selected page to a scratch file, `<pageId>-<slug>.md`, with a header carrying its id, title, URL, version and labels, then invokes `/speckit.constitution` once with the list of files in depth-first order (the rationalised files, when grounded). The invocation tells it to merge every source in one pass, to keep MUST/SHOULD/MAY wording exactly as written, and to cite the source page and section number for each rule (for example `Source: IaC Standards, 3.6.2`).

After the run the skill lists pages that the selected pages link to but that were not included, and why (no `steering` label, no matching `appliesto-*` label, outside the root, or index/empty), so gaps are easy to spot.

#### Documented exceptions

Approved deviations from the standards belong to the repository, under a `Documented Exceptions` section of `.specify/memory/constitution.md` (rule, deviation and source, rationale, approver and date, revisit criteria). The skill copies any existing section before generating, checks it afterwards and restores anything that was changed or dropped, and adds an empty table if there is no such section. Regeneration never removes or rewrites entries, including hand edits. Proposed exceptions from rationalisation are only ever appended.

#### Lock file and refreshing

After a run the skill writes `.specify/memory/constitution.lock.yaml`, recording the repo context and, for each page used, its ID, title, version, labels, why it was included and a SHA-256 hash of its content. Pages that were skipped are listed with the reason. For a grounded run it also records each grounding document (id, title, version, status, whether it is endorsed, content hash, and a hash of its notes) and every rationalisation decision (rule id, keep/adapt/drop, and a hash of the rule text). Commit it, the audit file and the constitution together.

Run the same command again to refresh. If a lock file exists, the skill compares the pages that apply now against the lock by content hash and reports which were added, removed or updated (a version bump with identical content counts as unchanged). If nothing changed it stops without regenerating (use `--force` to override). Otherwise it merges the full set of applicable pages again, telling `/speckit.constitution` what was added, updated and removed.

When rationalising again, earlier decisions are reused, so only rules that are new or whose text changed are put up for a decision. A dropped rule whose text changed is surfaced again. If a grounding document changed, dropped and adapted rules are re-examined. If a grounding entry's notes changed, every rule is. A decision you edited by hand in the audit table is respected, and stays pinned through grounding and notes changes.

`--rationalise-only` re-runs just the rationalisation: it takes the page set from the lock file and reuses page content from the session's working directory when the version matches, fetching only what is missing. It does not notice pages added to or removed from Confluence, so run without it for that.

#### Hierarchy traversal

Pages are discovered with a CQL search (`ancestor = <root> AND label = "steering"`), which is not depth-limited. The hierarchy is fetched separately, only to order pages depth-first. That listing uses an explicit `depth` of 10 (the most the Confluence tool accepts), follows pagination, and re-queries pages at the depth cap. The run reports the page count and greatest depth reached.

The skill only ever reads from Confluence.

#### Files in this skill

| Path | Purpose |
|---|---|
| `SKILL.md` | The workflow |
| `references/rationalisation.md` | The detail of the rationalisation phase (profile, classification rules, audit file layout) |
| `scripts/rules.py` | Standard-library Python helper for the parts that must be exact: splitting pages into rule units, hashing them, diffing against the lock file, and writing the audit table, rationalised sources and lock decisions. Needs `python3` |

> **Authentication:** The Atlassian MCP server requires authentication with your Atlassian account.

### `specify-from-jira`

Fetches a Jira ticket and uses it as context for `/speckit.specify`.

```
/speckit-extensions:specify-from-jira <jira-ticket-id> [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `jira-ticket-id` | Yes | Jira issue key, e.g. `PROJ-123` |
| `additional-input` | No | Extra context or instructions to include alongside the ticket |

**Example:**

```
/speckit-extensions:specify-from-jira PROJ-123
/speckit-extensions:specify-from-jira PROJ-123 focus on the mobile experience
```

### `plan-from-confluence`

Fetches a Confluence page and its full child hierarchy, feeding each page individually into `/speckit.plan`.

```
/speckit-extensions:plan-from-confluence <confluence-url> [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `confluence-url` | Yes | URL to a Confluence page, e.g. `https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Page+Title` |
| `additional-input` | No | Extra context or instructions passed as a separate invocation of `/speckit.plan` |

**Example:**

```
/speckit-extensions:plan-from-confluence https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/HLD
/speckit-extensions:plan-from-confluence https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/HLD focus on the data access layer
```

The skill parses the space key and page ID from the URL, recursively fetches all descendant pages depth-first via the Atlassian MCP server, and invokes `/speckit.plan` once per page. If additional input is provided, it is passed as a final separate invocation.

> **Authentication:** The Atlassian MCP server requires authentication with your Atlassian account.

### `plan-from-lucid`

Fetches a Lucidchart diagram page and uses it as context for `/speckit.plan`.

```
/speckit-extensions:plan-from-lucid <lucid-url> [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `lucid-url` | Yes | URL to a Lucidchart document page, including the `page` query parameter |
| `additional-input` | No | Extra context or instructions to include alongside the diagram |

**Example:**

```
/speckit-extensions:plan-from-lucid https://lucid.app/lucidchart/9c028565-3df6-4c34-9db4-449bb5c7c20d/edit?page=4WDSdv3BMKuG
/speckit-extensions:plan-from-lucid https://lucid.app/lucidchart/9c028565-3df6-4c34-9db4-449bb5c7c20d/edit?page=4WDSdv3BMKuG focus on the data layer
```

The skill parses the document ID and page ID from the URL, fetches the diagram from the Lucidchart MCP server in the most structured format available (SVG or XML preferred), and passes it along with any additional input to `/speckit.plan`.

> **Authentication:** The Lucidchart MCP server uses OAuth. You will be prompted to authenticate with your Lucid account on first use.

### `plan-from-swagger`

Fetches an OpenAPI spec from SwaggerHub and uses it as context for `/speckit.plan`.

```
/speckit-extensions:plan-from-swagger <swaggerhub-url> [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `swaggerhub-url` | Yes | URL to a SwaggerHub API spec, e.g. `https://api.swaggerhub.com/apis/MyOrg/MyAPI/1.0.0` |
| `additional-input` | No | Extra context or instructions to include alongside the spec |

**Example:**

```
/speckit-extensions:plan-from-swagger https://api.swaggerhub.com/apis/MyOrg/MyAPI/1.0.0
/speckit-extensions:plan-from-swagger https://api.swaggerhub.com/apis/MyOrg/MyAPI/1.0.0 focus on the authentication endpoints
```

The skill fetches the fully-resolved OpenAPI spec (JSON format) via the fetch-swagger MCP server, then passes it along with any additional input to `/speckit.plan`.

> **Authentication:** The SwaggerHub API requires an API key. Set `SWAGGERHUB_API_KEY` in your environment, or the skill will prompt you for it on first use.

## Updating

```sh
claude plugin update speckit-extensions
```

## Removing

```sh
claude plugin remove speckit-extensions
```

## Contributing

Skills live in `skills/<skill-name>/SKILL.md`. To add a new skill:

**1. Create the skill directory and file**

```
skills/
└── <skill-name>/
    └── SKILL.md
```

**2. Write the `SKILL.md`**

```markdown
---
name: <skill-name>
description: <when Claude (or the user) should invoke this skill>
user-invocable: true
argument-hint: <arg> [optional-arg]
---

# <skill-name>

...
```

Key frontmatter fields:

| Field | Description |
|---|---|
| `name` | Skill identifier — becomes the slash command suffix |
| `description` | Trigger conditions; used by Claude to decide when to invoke automatically |
| `user-invocable` | Set `true` to expose as `/speckit-extensions:<skill-name>` |
| `argument-hint` | Shown in the command palette to describe expected arguments |
| `allowed-tools` | Restrict which tools the skill may use (omit to allow all) |

**3. Follow the skill pattern**

Each skill in this plugin follows the same pattern:
1. Parse `$ARGUMENTS`
2. Fetch context from an external system via an MCP server
3. Compose a structured input block
4. Invoke the appropriate `/speckit.*` command

If the skill depends on an MCP server not already bundled by this plugin, add it to the `mcpServers` map in `.claude-plugin/plugin.json`. MCP servers are bundled directly (rather than declared as plugin dependencies) because plugin dependencies are not auto-installed at the time of writing.

**4. Open a pull request**

Submit a PR to this repository. Include an example invocation in the PR description.
