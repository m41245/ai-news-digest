# GitHub Environments, Variables, and Secrets

This document lists the exact GitHub repository settings required for the CI/CD workflows to function correctly.

## Required GitHub Environments

### staging
- **Protection rules:** None required (auto-deploy on CI pass)
- **Required reviewers:** None
- **Wait timer:** None

### production
- **Protection rules:**
  - Required reviewers: 1 (any team member with admin access)
  - Wait timer: 0 minutes
  - Restrict branches: `main` only
  - Allow force pushes: Disabled
  - Allow deletions: Disabled

## Required GitHub Variables

| Variable | Value | Environment | Required |
|----------|-------|-------------|----------|
| `STAGING_DEPLOY_HOST` | Staging server IP or hostname | staging | Yes (for automated staging deploy) |
| `STAGING_DEPLOY_USERNAME` | SSH username for staging | staging | Yes (for automated staging deploy) |
| `STAGING_DEPLOY_PORT` | SSH port (default: 22) | staging | No |
| `PROD_DEPLOY_HOST` | Production server IP or hostname | production | Yes (for automated production deploy) |
| `PROD_DEPLOY_USERNAME` | SSH username for production | production | Yes (for automated production deploy) |
| `PROD_DEPLOY_PORT` | SSH port (default: 22) | production | No |

## Required GitHub Secrets

| Secret | Description | Environment | Required |
|--------|-------------|-------------|----------|
| `GITHUB_TOKEN` | Auto-provided by GitHub Actions | All | Yes |
| `STAGING_DEPLOY_SSH_KEY` | Private SSH key for staging deployment | staging | Yes (for automated staging deploy) |
| `PROD_DEPLOY_SSH_KEY` | Private SSH key for production deployment | production | Yes (for automated production deploy) |
| `STAGING_ENV_FILE` | Base64-encoded `.env.prod.local` for staging | staging | No (if deploying via env-file) |
| `PROD_ENV_FILE` | Base64-encoded `.env.prod.local` for production | production | No (if deploying via env-file) |

## Required Container Registry Permissions

- **GitHub Container Registry (ghcr.io):**
  - Package visibility: Private (or public if desired)
  - Write permissions: Packages write (granted to GITHUB_TOKEN)
  - Image retention: Keep latest 10 images per branch/tag

## Workflow Triggers Summary

| Workflow | Trigger | Environments |
|----------|---------|--------------|
| CI | Push to main/master, PRs to main/master | All |
| Deploy Staging | Push to main/master/develop, manual dispatch | staging |
| Deploy | Tag push v*, release publish, manual dispatch with approval | staging, production |

## Manual Approval Requirements

Production deployment via `workflow_dispatch` requires:
- `environment` input set to `production`
- `approve_production` input set to `true`
- `approved_by` input set to the approver's name

When GitHub environment protection rules are configured for `production`, the deployment job will pause for required reviewer approval before proceeding.
