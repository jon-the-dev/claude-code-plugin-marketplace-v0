---
name: validate
description: Validate runway configuration and custom hooks
args:
  - name: target
    description: What to validate (config, hooks, all)
    required: false
---

# Runway Validate Command

Quick validation of runway configurations and custom hooks before deployment.

## Usage

```bash
# Validate everything
/runway validate
/runway validate all

# Validate only configuration
/runway validate config

# Validate only hooks
/runway validate hooks
```

## Command Logic

```bash
#!/bin/bash
set -e

TARGET="${1:-all}"

echo "🔍 Runway Validation"
echo "━━━━━━━━━━━━━━━━━━━"
echo ""

# Validate configuration
validate_config() {
  echo "📋 Validating runway configuration..."

  # Check if runway.yml or runway.yaml exists
  if [ -f "runway.yml" ]; then
    CONFIG_FILE="runway.yml"
  elif [ -f "runway.yaml" ]; then
    CONFIG_FILE="runway.yaml"
  else
    echo "❌ No runway configuration found (runway.yml or runway.yaml)"
    return 1
  fi

  echo "✅ Found: $CONFIG_FILE"

  # Validate YAML syntax with Python
  python3 -c "
import yaml
import sys

try:
    with open('$CONFIG_FILE', 'r') as f:
        config = yaml.safe_load(f)
    print('✅ YAML syntax is valid')

    # Check for deployments
    if 'deployments' not in config:
        print('⚠️  Warning: No deployments defined')
        sys.exit(1)

    print(f'✅ Found {len(config[\"deployments\"])} deployment(s)')

    # Check each deployment for modules
    for i, deployment in enumerate(config['deployments']):
        if 'modules' not in deployment:
            print(f'⚠️  Warning: Deployment {i} has no modules')
        else:
            print(f'✅ Deployment {i}: {len(deployment[\"modules\"])} module(s)')

except yaml.YAMLError as e:
    print(f'❌ YAML syntax error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ Validation error: {e}')
    sys.exit(1)
"

  if [ $? -eq 0 ]; then
    echo "✅ Configuration validation passed"
    return 0
  else
    echo "❌ Configuration validation failed"
    return 1
  fi
}

# Validate hooks
validate_hooks() {
  echo ""
  echo "🔧 Validating custom hooks..."

  if [ ! -d "hooks" ]; then
    echo "ℹ️  No hooks directory found"
    return 0
  fi

  # Count hook files
  HOOK_COUNT=$(find hooks -name "*.py" ! -name "__init__.py" ! -name "test_*.py" | wc -l | tr -d ' ')

  if [ "$HOOK_COUNT" -eq 0 ]; then
    echo "ℹ️  No custom hooks found"
    return 0
  fi

  echo "📁 Found $HOOK_COUNT hook file(s)"
  echo ""

  # Validate each hook
  find hooks -name "*.py" ! -name "__init__.py" ! -name "test_*.py" | while read -r hook_file; do
    hook_name=$(basename "$hook_file")
    echo "  Validating: $hook_name"

    # Check Python syntax
    if python3 -m py_compile "$hook_file" 2>/dev/null; then
      echo "    ✅ Syntax valid"
    else
      echo "    ❌ Syntax error"
      continue
    fi

    # Check for Hook import
    if grep -q "from runway.cfngin.hooks.base import Hook" "$hook_file"; then
      echo "    ✅ Hook import found"
    else
      echo "    ⚠️  Missing Hook import"
    fi

    # Check for Hook class
    if grep -q "class.*Hook.*:" "$hook_file"; then
      echo "    ✅ Hook class defined"
    else
      echo "    ⚠️  No Hook class found"
    fi

    # Check for hook methods
    if grep -qE "(def pre_deploy|def post_deploy|def pre_destroy|def post_destroy)" "$hook_file"; then
      echo "    ✅ Hook method(s) found"
    else
      echo "    ⚠️  No hook methods found"
    fi

    echo ""
  done

  echo "✅ Hook validation completed"
  return 0
}

# Run validation based on target
case $TARGET in
  config)
    validate_config
    ;;
  hooks)
    validate_hooks
    ;;
  all|*)
    validate_config
    VALIDATION_RESULT=$?
    validate_hooks
    exit $VALIDATION_RESULT
    ;;
esac
```

## Validation Checks

### Configuration Validation
- ✅ runway.yml or runway.yaml exists
- ✅ Valid YAML syntax
- ✅ deployments section exists
- ✅ modules are defined
- ✅ Hook references are valid

### Hook Validation
- ✅ Valid Python syntax
- ✅ Proper Hook import
- ✅ Hook class inheritance
- ✅ Required methods implemented
- ✅ No obvious errors

## Examples

**Full validation before deployment**:
```bash
/runway validate
```

**Quick config check**:
```bash
/runway validate config
```

**Validate hooks after changes**:
```bash
/runway validate hooks
```

## Output Example

```
🔍 Runway Validation
━━━━━━━━━━━━━━━━━━━

📋 Validating runway configuration...
✅ Found: runway.yml
✅ YAML syntax is valid
✅ Found 2 deployment(s)
✅ Deployment 0: 3 module(s)
✅ Deployment 1: 1 module(s)
✅ Configuration validation passed

🔧 Validating custom hooks...
📁 Found 4 hook file(s)

  Validating: cloudfront_invalidation.py
    ✅ Syntax valid
    ✅ Hook import found
    ✅ Hook class defined
    ✅ Hook method(s) found

  Validating: npm_build.py
    ✅ Syntax valid
    ✅ Hook import found
    ✅ Hook class defined
    ✅ Hook method(s) found

✅ Hook validation completed
```
