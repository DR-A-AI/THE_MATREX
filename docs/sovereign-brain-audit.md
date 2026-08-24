# Sovereign_Brain — Configuration Audit

**Date:** 2026-08-24
**Subject:** Copilot Studio agent `Sovereign_Brain`
**Agent id:** `290dc317-82c9-47d4-b962-36684477b10b`
**Schema name:** `crbab_sovereign_brain_RsSYXQ`
**Environment:** `Sovereign_Sandbox_v1` — `https://org331e3f60.crm.dynamics.com`
(env id `0697c607-6dde-e463-bbf6-62146ecda804`)
**Method:** read-only Dataverse queries against `bots` and `botcomponents`.
No write was attempted (see *Blocker*).

---

## Record baseline (verified live)

| Field | Value |
|---|---|
| `template` | `cliagent-1.0.0` |
| `statecode` / `statuscode` | `0` Active / `1` Provisioned |
| `createdon` | `2026-07-12T21:49:09Z` |
| `publishedon` | `2026-08-23T18:07:51Z` |
| `modifiedon` | `2026-08-23T18:08:26Z` |
| `@odata.etag` | `W/"12364021"` |
| `accesscontrolpolicy` | `2` (Group membership) |
| `authenticationmode` | `2` (Integrated) |
| `channels` | `MsTeams`, `Microsoft365Copilot` |
| `recognizer` | `CLICopilotRecognizer` |
| `agentSettings.model.series` | `claude-opus-5` |
| `enableMemory` | `true` |
| `web.enableWebSearch` | `true` |

Total attached components: **120** (queried with `top=5000`; no `nextLink`).
Breakdown: 97 `Topic (V2)`, 21 `Test Case`, 2 `Bot File Attachment`.
Prefix split: **87** `crbab_sovereign_brain_RsSYXQ`, **12** `crbab_draft_b30NYn`,
21 `mspva_*`.

---

## Defect 1 — Instruction field overwritten (PRIMARY)

`configuration.agentSettings.instructions.segments[0]` is a single
`StaticSegment` whose `value` is the **verbatim text of the awesome-copilot
`agents.instructions.md` authoring guide** — opening with
`description: 'Guidelines for creating custom agent files for GitHub Copilot'`
and `applyTo: '**/*.agent.md'`.

Approximately 30,000 characters of generic documentation about *how to write
`.agent.md` files*. It contains **zero** Sovereign_Brain identity, mission,
standing rules, or delegated-authority framing.

**Confirmation:** read twice, identical both times. The same text appears
verbatim in the agent's own running system prompt — proving it is the live
instruction set, not a stale draft.

**Effect:** the agent drifts toward behaving as a documentation assistant for
`.agent.md` files, because that is literally what its instructions describe.

**Fix:** replace with `.github/agents/sovereign-brain.agent.md` (this repo).

---

## Defect 2 — Duplicate GitHub MCP Server connection

Two GitHub MCP tool components are attached simultaneously:

| Component | Modified |
|---|---|
| `crbab_draft_b30NYn.tool.GitHub-GithubMCPServer_CTD` | `2026-08-23T16:50:01Z` |
| `crbab_sovereign_brain_RsSYXQ.tool.GitHub-GithubMCPServer1_i0_` | `2026-08-23T16:51:36Z` |

The second was added 95 seconds after the first and is named
"GitHub — Github MCP Server **1**".

**Confirmed live symptom:** every GitHub tool is exposed twice, the second
carrying a `_2` suffix — `create_branch` / `create_branch_2`, `issue_read` /
`issue_read_2`, `merge_pull_request` / `merge_pull_request_2`, and roughly 40
further pairs. This inflates the tool surface and creates ambiguous routing.

**Fix:** delete the older `crbab_draft_b30NYn.tool.GitHub-GithubMCPServer_CTD`.

---

## Defect 3 — Orphaned draft-prefix components (12)

All `Active`, all `Topic (V2)`, all created `2026-07-12T21:49:xx` — the agent's
creation timestamp. These are legacy bindings under the pre-rename draft prefix
`crbab_draft_b30NYn` that were never migrated when the agent was renamed to
`crbab_sovereign_brain_RsSYXQ`.

```
crbab_draft_b30NYn.tool.WorkIQUserPreview_ckL
crbab_draft_b30NYn.tool.WorkIQCopilotPreview_LCv
crbab_draft_b30NYn.tool.ExecuteAgent_Xbj
crbab_draft_b30NYn.tool.ExecuteAgentandwait_JYX
crbab_draft_b30NYn.tool.GetAgentTestSets_oYh
crbab_draft_b30NYn.tool.GetAgentTestSetDetails_onl
crbab_draft_b30NYn.tool.GetAgentTestRuns_b25
crbab_draft_b30NYn.tool.EvaluateAgent_u0k
crbab_draft_b30NYn.tool.GetscopytargetcandidateenvironmentsPreview_xtY
crbab_draft_b30NYn.tool.GitHub-GithubMCPServer_CTD
crbab_draft_b30NYn.tool.Sendactivitytoagent_rRR
crbab_draft_b30NYn.skill.s1_WRg
```

**Fix:** delete all 12.

---

## Defect 4 — Configuration gaps

- `settings` is `{"AnonymousAccessDisabled": false}` — **anonymous access is
  enabled** on an agent published to `MsTeams` and `Microsoft365Copilot`. The
  sibling agent `neo` in the same environment sets this to `true`.
- **No `aISettings` block exists at all.** Consequently there is no
  `contentModeration` setting (`neo` uses `"High"`), and no
  `useModelKnowledge`, `isFileAnalysisEnabled`, `isSemanticSearchEnabled`, or
  `optInUseLatestModels`.
- `modifiedon` (`2026-08-23T18:08:26Z`) is **35 seconds after** `publishedon`
  (`2026-08-23T18:07:51Z`) — there are already unpublished pending changes.
  This predates this audit.

**Fix:** set `AnonymousAccessDisabled: true`; add an `aISettings` block with
`contentModeration: "High"`.

---

## Blocker — no Dataverse write path

The available Dataverse tool surface is:

```
GetOrganizations
GetEntitiesWithOrganization
GetMetadataForGetEntityWithOrganization
GetMetadataForPostEntityWithOrganization
GetRelevantRows
ListRecords
ListRecordsWithOrganization
create_record_with_organization
get_item_with_organization
```

There is **no update, patch, or delete tool**. Rows can be created but not
modified or removed. `UpdateRecordWithOrganization`,
`UpdateOnlyRecordWithOrganization`, `PerformBoundActionWithOrganization`, and
`PerformUnboundActionWithOrganization` are *named inside other tools' help text*
but are **not exposed as callable tools**. The Power Platform Admins V2 surface
(`EnvironmentManagement_*`) manages environments, not `bots` records.

**Therefore defects 1–4 cannot be remediated programmatically from this agent.**
They require the Copilot Studio console.

---

## Evaluation-harness limitation

Test set **"Evaluate Agent"** — `2dc2147a-ab28-4084-bd16-b6f4eefb61f3`, Active,
20 cases. Five historical runs, all `state: Completed`:

| Run id | Started | Duration | Cases |
|---|---|---|---|
| `73668340-e294-4773-9a05-105deb68dab0` | 2026-08-14T11:34:14Z | ~5m13s | 20 |
| `3c383750-e253-4e09-888e-420dff165885` | 2026-08-14T11:26:40Z | ~7m04s | 20 |
| `45f5b04c-e6b0-47ee-aab6-a37c047dd744` | 2026-08-13T14:45:37Z | ~4m23s | 10 |
| `8d137909-fd9f-44df-b080-c9e37bee2275` | 2026-08-08T12:36:43Z | ~62m29s | 10 |
| `76f7bb28-0c36-4d9c-8a9f-51a1696ddf3f` | 2026-08-05T16:23:43Z | ~72m42s | 10 |

`testCasesResults` is `[]` on **every** run — per-case scores are not returned.
`GetAgentTestSetDetails` accepts a *test-set* id, not a run id.

**Consequence:** `EvaluateAgent` can confirm only completion and duration. It is
a weak gate and must not be presented as pass/fail proof.

---

## Remediation checklist (Copilot Studio console)

1. Replace the instructions with `.github/agents/sovereign-brain.agent.md`.
2. Delete the duplicate connection
   `crbab_draft_b30NYn.tool.GitHub-GithubMCPServer_CTD`.
3. Delete the 12 orphaned `crbab_draft_b30NYn.*` components listed above.
4. Set `AnonymousAccessDisabled: true` and add `aISettings` with
   `contentModeration: "High"`.
5. Re-publish (note: unpublished changes were already pending before this
   audit).
