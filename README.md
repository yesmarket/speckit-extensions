# speckit-extensions

A Claude Code plugin for AI-assisted spec-driven development. Provides skills that gather context from external systems such as Jira, Confluence, Figma, and others, and pipes it into [speckit](https://github.com/github/spec-kit) commands to drive spec driven development workflows.

## Installation

**1. Add the marketplace**

```sh
claude plugin marketplace add yesmarket/claude-marketplace
```

**2. Install the plugin**

```sh
claude plugin install speckit-extensions@yesmarket/claude-marketplace
```

This will also install the [Atlassian](https://github.com/atlassian/atlassian-mcp-server) plugin dependency, which provides the MCP server and skills for Jira and Confluence.

## Skills

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

## Updating

```sh
claude plugin update speckit-extensions
```

## Removing

```sh
claude plugin remove speckit-extensions
```

This does not remove the `atlassian` dependency — remove it separately if it is no longer needed:

```sh
claude plugin remove atlassian
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

If the skill depends on an MCP server that isn't already provided by the `atlassian` dependency, add the plugin that provides it to the `dependencies` array in `.claude-plugin/plugin.json`.

**4. Open a pull request**

Submit a PR to this repository. Include an example invocation in the PR description.
