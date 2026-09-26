---
name: use-sovereign-auditor
description: >
  Auto-triggers when the user or project needs a security audit, code quality review,
  shell=False compliance check, secret leak scanning, Aegis QA gate inspection, or AST
  vulnerability analysis on Python, JavaScript, TypeScript, or bash files. Use this whenever
  reviewing PRs, verifying subagent deliverables, auditing subprocess executions, or checking
  cryptographic bus message integrity.
---

# Use Sovereign Security & Code Auditor

When code security, static quality gates, subprocess execution safety (`shell=False`), token leak prevention, or bus message schema verification is requested, delegate the task to the `sovereign-auditor` subagent instead of handling it in the main thread.

## When to delegate

| User says / context | Action |
|---|---|
| "افحص الأمان", "تحقق من الكود", "security audit", "audit this module" | Delegate to `sovereign-auditor` |
| "تحقق من shell=False", "check for subprocess vulnerabilities", "bandit scan" | Delegate to `sovereign-auditor` |
| "هل هناك تسريب مفاتيح؟", "scan for secret leaks", "verify token masking" | Delegate to `sovereign-auditor` |
| "راجع بوابات الجودة", "Aegis QA gate check", "review PR / deliverable security" | Delegate to `sovereign-auditor` |
| Simple typo fix or 1-line variable rename | Handle in main thread |

## How to delegate

Package the user's audit request and invoke the `sovereign-auditor` subagent using `invoke_subagent`. Include:
1. Exact file paths or directories targeted for audit.
2. Context of recent modifications or proposed changes.
3. Specific security invariants to check (e.g. `shell=False`, secret masking, async loop non-blocking).

Example delegation prompt:
```
Perform a rigorous security and code quality audit on `agents/neo_agent.py` and `services/safe_shell.py`.
Verify:
1. Strict `shell=False` compliance on all subprocess invocations.
2. Zero leakage or unmasked logging of keys/tokens (`***{last4}`).
3. Safe path resolution avoiding directory traversal.
Return the standard Sovereign Security & Code Audit Report with actionable drop-in diffs.
```

## What to expect back

The `sovereign-auditor` returns a structured report adhering to the standard schema:
1. **Executive Summary**: Scope, overall verdict (PASSED / FAILED / CONDITIONALLY APPROVED), and key takeaways.
2. **Security & Compliance Matrix**: Count of findings grouped by severity (Blocker, Warning, Advisory).
3. **Detailed Findings**: Specific file and line references, root cause analysis, and drop-in remediation diffs.
4. **Verification Checkpoints**: Checklist confirming key defenses are verified.
