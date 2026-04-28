---
name: specify-from-jira
description: Use when the user wants to create a feature spec from a Jira ticket — e.g. "specify from jira PROJ-123", "/speckit-extensions:specify-from-jira PROJ-123", or "write a spec for <ticket>". Queries the Jira ticket via the Atlassian MCP server and pipes the ticket context into /speckit.specify to produce a feature spec.
user-invocable: true
argument-hint: <jira-ticket-id> [additional-input]
---

# specify-from-jira

Pull a Jira ticket and use its content as context for `/speckit.specify`.

## Arguments

`$ARGUMENTS` contains: `<jira-ticket-id> [additional-input]`

- `jira-ticket-id` (required): Jira issue key, e.g. `PROJ-123`
- `additional-input` (optional): Extra context or instructions to include alongside the ticket

## Steps

### 1. Parse Arguments

Extract the Jira ticket ID (first whitespace-delimited token from `$ARGUMENTS`) and any additional input (everything after it).

### 2. Fetch Jira Ticket

**IMPORTANT: Only perform read operations against Jira. Never create, edit, or delete Jira issues, comments, or any other Jira resources.**

Using the Atlassian MCP server, retrieve the following for the ticket:

- **Summary** — the issue title
- **Description** — full issue body
- **Acceptance criteria** — dedicated field or section within the description
- **Comments** — all comments on the issue (author, date, body)
- **Linked issues and subtasks** — key, summary, and link type for each

### 3. Compose Context

Format the retrieved data into a feature description block:

```
Jira Ticket: <ticket-id>
Summary: <summary>

Description:
<description>

Acceptance Criteria:
<acceptance criteria, or "N/A" if not present>

Comments:
<author> (<date>): <body>
...

Linked Issues / Subtasks:
- <link-type> <key>: <summary>
...
```

Append any additional input from `$ARGUMENTS` after the above block.

### 4. Invoke /speckit.specify

Pass the composed context block as the feature description to `/speckit.specify`.
