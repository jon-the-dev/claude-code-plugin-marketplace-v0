---
name: deploy
description: Execute runway deployment with environment and tag filtering
args:
  - name: environment
    description: Target deployment environment (dev, staging, prod, etc.)
    required: false
  - name: tags
    description: Tag filter for selective deployment (e.g., app:frontend)
    required: false
  - name: dry-run
    description: Run plan instead of deploy to preview changes
    required: false
    type: boolean
---

# Runway Deploy Command

Quick command to execute runway deployments with environment management and tag filtering.

## Usage

```bash
# Basic deployment
/runway deploy

# Environment-specific deployment
/runway deploy dev
/runway deploy staging
/runway deploy prod

# Tag-filtered deployment
/runway deploy --tags app:frontend
/runway deploy staging --tags component:api

# Dry run (plan mode)
/runway deploy prod --dry-run
```

## Command Logic

```bash
#!/bin/bash
set -e

# Parse arguments
ENVIRONMENT="${1:-}"
TAGS=""
DRY_RUN=false

# Parse flags
while [[ $# -gt 0 ]]; do
  case $1 in
    --tags)
      TAGS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      if [ -z "$ENVIRONMENT" ]; then
        ENVIRONMENT="$1"
      fi
      shift
      ;;
  esac
done

# Build runway command
if [ "$DRY_RUN" = true ]; then
  CMD="runway plan"
else
  CMD="runway deploy"
fi

# Add environment if specified
if [ -n "$ENVIRONMENT" ]; then
  CMD="$CMD --deploy-environment $ENVIRONMENT"
fi

# Add tags if specified
if [ -n "$TAGS" ]; then
  CMD="$CMD --tag $TAGS"
fi

# Display command
echo "🚀 Executing: $CMD"
echo ""

# Execute runway
$CMD
```

## Examples

**Deploy to development**:
```bash
/runway deploy dev
```

**Deploy only frontend to staging**:
```bash
/runway deploy staging --tags app:frontend
```

**Preview production changes**:
```bash
/runway deploy prod --dry-run
```

**Deploy specific component**:
```bash
/runway deploy --tags component:database
```
