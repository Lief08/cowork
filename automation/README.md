# Automation

This directory contains automation scripts, CI/CD configurations, Infrastructure-as-Code, and solution implementations.

## Contents

- Shell/Python/other scripts
- CI/CD pipeline definitions (GitHub Actions, etc.)
- Infrastructure-as-Code (Terraform, CloudFormation, etc.)
- Automation solutions and tooling

## When to add something here

- You've built a script or tool to automate a task
- You're adding CI/CD pipelines or workflow automation
- You're implementing an infrastructure or deployment solution

## Subdirectory suggestions

```
automation/
├── scripts/      # One-off or utility scripts
├── pipelines/    # CI/CD and workflow definitions
├── iac/          # Infrastructure-as-Code
└── solutions/    # Larger automation solutions
```

## File naming

Use descriptive names that convey purpose:
- `scripts/sync-repos.sh`
- `pipelines/deploy-staging.yml`
- `iac/vpc-setup.tf`
