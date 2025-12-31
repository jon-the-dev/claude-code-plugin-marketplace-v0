---
event: PreToolUse
description: Validate runway configurations before deployment commands
---

# Runway Configuration Validation Hook

This hook intercepts bash commands related to runway deployments and validates configurations before execution to prevent failures.

## Hook Behavior

When Claude attempts to run runway commands, this hook:
1. Detects runway-related bash commands
2. Validates runway configuration exists and is valid
3. Checks for common issues
4. Allows/blocks command execution based on validation

## Triggered Commands

This hook activates for commands containing:
- `runway deploy`
- `runway plan`
- `runway destroy`
- `runway init`

## Validation Logic

```bash
#!/bin/bash

# Extract the command from the tool use
COMMAND="{{TOOL_INPUT.command}}"

# Check if this is a runway command
if [[ ! "$COMMAND" =~ runway[[:space:]]+(deploy|plan|destroy|init) ]]; then
  # Not a runway command, allow it
  exit 0
fi

echo "🔍 Validating runway configuration before execution..."

# Check for runway configuration
if [ ! -f "runway.yml" ] && [ ! -f "runway.yaml" ]; then
  echo "❌ Error: No runway configuration found (runway.yml or runway.yaml)"
  echo ""
  echo "Please create a runway configuration file first:"
  echo "  touch runway.yml"
  echo ""
  echo "Or initialize runway:"
  echo "  runway init"
  exit 1
fi

# Determine config file
if [ -f "runway.yml" ]; then
  CONFIG_FILE="runway.yml"
else
  CONFIG_FILE="runway.yaml"
fi

echo "✅ Found configuration: $CONFIG_FILE"

# Validate YAML syntax
python3 -c "
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)

    # Basic validation
    if config is None:
        print('❌ Error: Configuration file is empty')
        sys.exit(1)

    if 'deployments' not in config:
        print('⚠️  Warning: No deployments defined in configuration')
        sys.exit(1)

    if len(config['deployments']) == 0:
        print('⚠️  Warning: No deployment modules configured')
        sys.exit(1)

    print(f'✅ Configuration valid: {len(config[\"deployments\"])} deployment(s) defined')

except yaml.YAMLError as e:
    print(f'❌ Error: Invalid YAML syntax')
    print(f'   {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: Configuration validation failed')
    print(f'   {e}')
    sys.exit(1)
" 2>&1

VALIDATION_RESULT=$?

if [ $VALIDATION_RESULT -ne 0 ]; then
  echo ""
  echo "❌ Configuration validation failed"
  echo ""
  echo "Please fix the configuration before proceeding."
  echo "You can validate with: /runway validate"
  exit 1
fi

# Check for deployment environment in command
if [[ "$COMMAND" =~ --deploy-environment ]]; then
  ENV=$(echo "$COMMAND" | grep -oP '(?<=--deploy-environment )[^ ]+' || echo "")
  if [ -n "$ENV" ]; then
    echo "🌍 Target environment: $ENV"

    # Warn for production deployments
    if [[ "$ENV" =~ ^(prod|production)$ ]] && [[ "$COMMAND" =~ deploy ]]; then
      echo ""
      echo "⚠️  WARNING: Deploying to PRODUCTION environment!"
      echo "   Consider running 'runway plan --deploy-environment $ENV' first"
      echo ""
    fi
  fi
fi

# Check for hooks referenced in config
python3 -c "
import yaml
from pathlib import Path

with open('$CONFIG_FILE', 'r') as f:
    config = yaml.safe_load(f)

missing_hooks = []

for deployment in config.get('deployments', []):
    for module in deployment.get('modules', []):
        # Check pre_deploy hooks
        for hook in module.get('pre_deploy', []):
            hook_path = hook.get('path', '')
            if hook_path and not Path(hook_path).exists():
                missing_hooks.append(hook_path)

        # Check post_deploy hooks
        for hook in module.get('post_deploy', []):
            hook_path = hook.get('path', '')
            if hook_path and not Path(hook_path).exists():
                missing_hooks.append(hook_path)

if missing_hooks:
    print('⚠️  Warning: Missing hook files:')
    for hook in set(missing_hooks):
        print(f'   - {hook}')
    print('')
" 2>&1

echo "✅ Pre-deployment validation complete"
echo ""

# Allow the command to proceed
exit 0
```

## Validation Checks

1. **Configuration File**
   - runway.yml or runway.yaml exists
   - File is not empty
   - Valid YAML syntax

2. **Configuration Content**
   - deployments section exists
   - At least one deployment defined
   - Modules are configured

3. **Hook References**
   - Referenced hooks exist
   - Warns about missing files

4. **Environment Safety**
   - Detects production deployments
   - Suggests dry-run for prod

## Hook Response

### Success (Exit 0)
- Configuration is valid
- Command proceeds with execution
- Warnings displayed if applicable

### Failure (Exit 1)
- Configuration missing or invalid
- Command is blocked
- Error message with guidance

## Examples

### Blocked: Missing Configuration
```
🔍 Validating runway configuration before execution...
❌ Error: No runway configuration found (runway.yml or runway.yaml)

Please create a runway configuration file first:
  touch runway.yml

Or initialize runway:
  runway init

🚫 Command blocked by PreToolUse hook
```

### Blocked: Invalid YAML
```
🔍 Validating runway configuration before execution...
✅ Found configuration: runway.yml
❌ Error: Invalid YAML syntax
   mapping values are not allowed here
     in "runway.yml", line 5, column 10

❌ Configuration validation failed

Please fix the configuration before proceeding.
You can validate with: /runway validate

🚫 Command blocked by PreToolUse hook
```

### Warning: Production Deployment
```
🔍 Validating runway configuration before execution...
✅ Found configuration: runway.yml
✅ Configuration valid: 2 deployment(s) defined
🌍 Target environment: prod

⚠️  WARNING: Deploying to PRODUCTION environment!
   Consider running 'runway plan --deploy-environment prod' first

✅ Pre-deployment validation complete

✅ Command allowed to proceed
```

### Success: Valid Configuration
```
🔍 Validating runway configuration before execution...
✅ Found configuration: runway.yml
✅ Configuration valid: 2 deployment(s) defined
🌍 Target environment: dev
✅ Pre-deployment validation complete

✅ Command allowed to proceed
```

## Benefits

1. **Early Error Detection** - Catch configuration issues before deployment
2. **Safety Guards** - Warn about production deployments
3. **Missing Dependencies** - Alert about missing hook files
4. **Better DX** - Clear error messages with actionable guidance
5. **Confidence** - Know configuration is valid before execution

## Configuration

The hook is automatically active when:
- Runway skill is loaded
- User attempts runway deployment commands
- No manual configuration needed

To disable temporarily, use:
```bash
# Execute command directly without validation
runway deploy  # Hook still validates

# Or bypass via shell
bash -c "runway deploy"
```

## Integration with Other Components

- **Works with**: `/runway deploy` command
- **Complements**: runway-validate-hooks agent
- **Prevents**: Invalid deployments and configuration errors
- **Suggests**: `/runway validate` for detailed checks

This hook provides automatic safety checks without requiring explicit user action, making runway deployments more reliable and error-free.
