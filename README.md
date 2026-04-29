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

### `constitution-from-confluence`

Fetches a Confluence page and its full child hierarchy, feeding each page individually into `/speckit.constitution`.

```
/speckit-extensions:constitution-from-confluence <confluence-url> [additional-input]
```

**Arguments:**

| Argument | Required | Description |
|---|---|---|
| `confluence-url` | Yes | URL to a Confluence page, e.g. `https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Page+Title` |
| `additional-input` | No | Extra context or instructions passed as a separate invocation of `/speckit.constitution` |

**Example:**

```
/speckit-extensions:constitution-from-confluence https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Home
/speckit-extensions:constitution-from-confluence https://mycompany.atlassian.net/wiki/spaces/PROJ/pages/123456789/Home focus on the authentication domain
```

The skill parses the space key and page ID from the URL, recursively fetches all descendant pages depth-first via the Atlassian MCP server, and invokes `/speckit.constitution` once per page. If additional input is provided, it is passed as a final separate invocation.

> **Authentication:** The Atlassian MCP server requires authentication with your Atlassian account.

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
