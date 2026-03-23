# Contributing & Workflow Guide

This document describes how to use branches, structure work, and collaborate in this repository.

## Branch Lifecycle

```
main
 └── arch/api-gateway-design     ← isolated task branch
 └── process/onboarding-runbook  ← isolated task branch
 └── auto/deploy-pipeline        ← isolated task branch
```

### 1. Create a branch

Always branch off `main` (or the appropriate base branch):

```bash
git checkout main
git pull
git checkout -b <type>/<short-description>
```

### 2. Work on the task

- Copy `templates/task-branch.md` into the relevant directory and rename it appropriately.
- Commit frequently with descriptive messages.
- Keep each branch focused on a single task or topic.

### 3. Open a PR (optional but recommended)

Opening a PR — even a draft — creates a permanent, reviewable record of the work and Claude's output.

### 4. Merge or archive

- **Merge** into `main` when the work is complete and ready to incorporate.
- **Leave open** as a long-running branch for ongoing work (e.g., a living architecture doc).
- **Close without merging** to archive exploratory work that won't be adopted.

---

## Commit Message Style

```
<type>: <short summary>

[optional longer description]
```

Types: `arch`, `process`, `auto`, `docs`, `chore`, `fix`

Examples:
```
arch: add ADR for service mesh adoption
process: draft onboarding runbook v1
auto: add GitHub Actions deploy workflow
docs: update README with new structure
```

---

## Directory Conventions

| Directory      | What goes here                                              |
|----------------|-------------------------------------------------------------|
| `architecture/`| ADRs, design docs, diagrams, technical strategy notes       |
| `processes/`   | Runbooks, SOPs, checklists, workflow definitions            |
| `automation/`  | Scripts, CI/CD configs, IaC, pipeline definitions           |
| `docs/`        | General reference docs, meeting notes, research             |
| `templates/`   | Reusable starting points for new branches/tasks             |

---

## Adding a New Task

1. Check the `templates/` directory for a starting template.
2. Create a branch using the naming convention in [README.md](README.md).
3. Add your work in the appropriate directory.
4. Reference the task in a PR description so it's easy to find later.
