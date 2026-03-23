# cowork

A generalized repository for AI-assisted (Claude) work across architectural, process-oriented, and automation tasks.

## Purpose

This repository serves as a centralized workspace for managing work done in collaboration with Claude AI, including:

- **Architecture** – system design, diagrams, ADRs (Architecture Decision Records), and technical strategies
- **Processes** – workflows, runbooks, SOPs, and process documentation
- **Automation** – scripts, pipelines, and solution implementations

## Repository Structure

```
cowork/
├── architecture/   # Architectural decisions, designs, and diagrams
├── automation/     # Automation scripts, pipelines, and solutions
├── docs/           # General documentation and reference material
├── processes/      # Process documentation, runbooks, and SOPs
└── templates/      # Reusable templates for branches and tasks
```

## Branch Workflow

Each distinct task or subtopic lives on its own branch, keeping work isolated and reviewable.

**Branch naming convention:**

| Type        | Pattern                        | Example                            |
|-------------|--------------------------------|------------------------------------|
| Architecture | `arch/<short-description>`    | `arch/api-gateway-design`          |
| Process      | `process/<short-description>` | `process/onboarding-runbook`       |
| Automation   | `auto/<short-description>`    | `auto/deploy-pipeline`             |
| General/docs | `docs/<short-description>`    | `docs/quarterly-review`            |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full branch lifecycle and workflow details.

## Getting Started

1. **Clone the repo**
   ```bash
   git clone https://github.com/Lief08/cowork.git
   cd cowork
   ```

2. **Create a branch for your task**
   ```bash
   git checkout -b arch/my-new-design
   ```

3. **Use the task template** from `templates/task-branch.md` to structure your work.

4. **Open a PR** when the task is ready for review or to preserve a snapshot.

## Working with Claude

When starting a new task with Claude, include the relevant context from this repository (e.g., existing architecture docs or prior process decisions) so that Claude can provide consistent, informed assistance.

Suggested prompt structure:
```
Context: [paste relevant doc or describe current state]
Goal: [what you want to accomplish]
Type: [architecture | process | automation]
```
