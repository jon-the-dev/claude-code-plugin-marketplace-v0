---
name: runway
description: Comprehensive Runway infrastructure deployment management with agents, commands, and hooks
allowed-tools: Read, Bash, Edit, Write, Glob, Grep, TodoWrite, AskUserQuestion
---

# Runway Skill - Complete Infrastructure Deployment Suite

A comprehensive Claude Code skill for managing Runway infrastructure deployments with intelligent agents, convenient commands, and automatic validation.

## Overview

This skill provides everything you need to work with Runway (AWS CloudFormation/Terraform orchestrator):

- **4 Specialized Agents** - Autonomous workers for complex tasks
- **2 Slash Commands** - Quick access to common operations
- **1 Event Hook** - Automatic validation and safety checks
- **6 Example Hooks** - Ready-to-use deployment automation
- **2 MCP Servers** - CloudFormation and Terraform intelligence

## 🔌 MCP Server Integration

This skill automatically loads two powerful MCP servers that give agents deep infrastructure knowledge:

### AWS CloudFormation MCP Server
**Provides**:
- CloudFormation template validation and linting
- Resource property lookup and documentation
- Template introspection and analysis
- Best practices recommendations
- CFN-Lint integration

**Use cases**:
- Validate CloudFormation templates before deployment
- Get documentation for resource types
- Understand template structure and dependencies
- Debug template errors

### Terraform MCP Server
**Provides**:
- Terraform configuration validation
- Resource documentation and schemas
- Module analysis
- State file inspection
- Provider information

**Use cases**:
- Validate Terraform configurations
- Understand resource schemas
- Analyze module dependencies
- Debug Terraform issues

### How Agents Use MCP Servers

When you ask agents to work with runway configurations, they can now:

```
You: "Validate my CloudFormation template before deploying with runway"

Agent (using cfn-mcp-server):
- Uses cfn-lint tools to validate template
- Checks for security issues
- Validates resource properties
- Suggests improvements
- Then proceeds with runway deployment
```

```
You: "Check if my Terraform configuration is valid before runway deploy"

Agent (using terraform-mcp-server):
- Validates Terraform syntax
- Checks resource schemas
- Identifies configuration issues
- Provides detailed error messages
- Then executes runway deployment
```

**Configuration**: See `.mcp.json` for MCP server settings. The servers are automatically available to all agents.

## 🤖 Agents

Agents are autonomous AI workers that handle complex, multi-step tasks. They have specialized knowledge and can use multiple tools.

### runway-deploy
**Purpose**: Execute deployments with environment management and validation

**When to use**:
- Deploying infrastructure to AWS
- Environment-specific deployments (dev, staging, prod)
- Tag-based selective deployments
- Running deployment dry-runs

**Capabilities**:
- ✅ Environment validation and configuration
- ✅ Tag-based deployment filtering
- ✅ Custom hook execution
- ✅ Deployment orchestration and monitoring
- ✅ Safety checks for production deployments
- ✅ Error handling and rollback guidance

**Example invocations**:
```
"Deploy to production using runway"
"Run runway deployment for staging environment"
"Deploy with tags app:frontend"
```

### runway-local-dev
**Purpose**: Manage local development environments with Docker Compose

**When to use**:
- Setting up local development environment
- Testing runway configurations locally
- Developing custom hooks
- Running services locally (databases, LocalStack, etc.)

**Capabilities**:
- ✅ Docker Compose environment setup
- ✅ LocalStack AWS service emulation
- ✅ Service orchestration and health monitoring
- ✅ Hot-reload for configuration changes
- ✅ Local testing and validation

**Example invocations**:
```
"Set up runway local environment"
"Start local development with docker"
"Configure LocalStack for runway testing"
```

### runway-validate-hooks
**Purpose**: Validate custom hooks before deployment

**When to use**:
- Before deploying with new hooks
- After modifying existing hooks
- Debugging hook failures
- Ensuring hook best practices

**Capabilities**:
- ✅ Hook syntax validation
- ✅ Dependency checking
- ✅ Functional testing
- ✅ Best practice recommendations
- ✅ Automated validation scripts

**Example invocations**:
```
"Validate my runway hooks"
"Check if my hook is correct"
"Test hooks before deployment"
```

### runway-create-hook
**Purpose**: Create new custom hooks following best practices

**When to use**:
- Creating new deployment automation
- Extending runway functionality
- Integrating external services
- Automating deployment workflows

**Capabilities**:
- ✅ Interactive hook scaffolding
- ✅ Template generation with best practices
- ✅ Test file creation
- ✅ Documentation generation
- ✅ Validation script creation

**Example invocations**:
```
"Create a new runway hook"
"I need a hook that invalidates cache"
"Build a custom deployment hook"
```

## 📝 Commands

Commands are simple slash commands for quick operations. They execute bash scripts with arguments.

### /runway deploy [environment] [--tags TAG] [--dry-run]
Quick deployment execution with environment and tag filtering

**Arguments**:
- `environment` - Target environment (dev, staging, prod)
- `--tags` - Tag filter for selective deployment
- `--dry-run` - Preview changes without deploying

**Examples**:
```bash
/runway deploy                          # Deploy everything
/runway deploy dev                      # Deploy to dev
/runway deploy staging --tags app:api   # Deploy API to staging
/runway deploy prod --dry-run           # Preview prod changes
```

### /runway validate [target]
Validate runway configuration and hooks

**Arguments**:
- `target` - What to validate: `config`, `hooks`, or `all` (default)

**Examples**:
```bash
/runway validate           # Validate everything
/runway validate config    # Config only
/runway validate hooks     # Hooks only
```

## 🪝 Event Hooks

Event hooks automatically trigger on Claude Code events to provide safety and validation.

### PreToolUse Hook
**Event**: PreToolUse (before bash commands execute)

**Purpose**: Automatically validate runway configurations before deployment commands

**When it triggers**:
- Before any `runway deploy` command
- Before any `runway plan` command
- Before any `runway destroy` command
- Before any `runway init` command

**What it validates**:
- ✅ Configuration file exists
- ✅ Valid YAML syntax
- ✅ Deployments are defined
- ✅ Referenced hooks exist
- ⚠️ Warns about production deployments

**Behavior**:
- **Blocks** command if validation fails
- **Warns** about production deployments
- **Allows** command if validation passes

**Example output**:
```
🔍 Validating runway configuration before execution...
✅ Found configuration: runway.yml
✅ Configuration valid: 2 deployment(s) defined
🌍 Target environment: dev
✅ Pre-deployment validation complete
```

## 📚 Example Hooks

Ready-to-use hooks in `examples/hooks/` for common deployment tasks:

| Hook | Description | Use Case | Stage |
|------|-------------|----------|-------|
| `cloudfront_invalidation` | Invalidate CloudFront distributions | Clear CDN cache after deployment | post_deploy |
| `docker_build_push` | Build and push Docker images to ECR | Container Lambda deployments | pre_deploy |
| `docker_compose_integration` | Start/stop Docker Compose services | Local development automation | pre_deploy |
| `env_file_generator` | Generate .env from stack outputs | Next.js/Node.js configuration | post_deploy |
| `npm_build` | Build and sync Next.js apps to S3 | Static site deployments | pre_deploy |
| `sam_deploy` | Deploy AWS SAM templates | Serverless applications | deployment |

Each hook includes:
- ✅ Full implementation
- ✅ Unit tests (`test_*.py`)
- ✅ Validation scripts (`validate_*.py`)
- ✅ Usage documentation

## 🚀 Quick Start

### 1. Basic Deployment
```bash
# Validate configuration
/runway validate

# Deploy to development
/runway deploy dev

# Or use the agent for complex deployments
"Deploy the application to staging with tag filtering"
```

### 2. Local Development
```bash
# Set up local environment
"Set up runway local development environment"

# This will:
# - Create docker-compose.yml with LocalStack
# - Configure local runway settings
# - Start development services
# - Set up environment variables
```

### 3. Create Custom Hook
```bash
# Create a new hook
"Create a runway hook that sends Slack notifications after deployment"

# This will:
# - Generate hook scaffolding
# - Create test files
# - Add validation scripts
# - Provide usage examples
```

### 4. Validate Before Deploy
```bash
# Validate hooks
"Validate my custom runway hooks"

# Validate configuration
/runway validate config

# The PreToolUse hook will also auto-validate before any deployment
```

## 🏗️ Skill Architecture

```
runway/
├── SKILL.md                          # This file
├── .mcp.json                         # MCP server configuration
├── agents/                           # Autonomous AI workers
│   ├── runway-deploy.md              # Deployment orchestration
│   ├── runway-local-dev.md           # Local environment management
│   ├── runway-validate-hooks.md      # Hook validation
│   └── runway-create-hook.md         # Hook creation
├── commands/                         # Slash commands
│   ├── deploy.md                     # /runway deploy
│   └── validate.md                   # /runway validate
├── hooks/                            # Event hooks
│   └── PreToolUse.md                 # Pre-command validation
└── examples/                         # Example implementations
    └── hooks/                        # Ready-to-use hooks
        ├── cloudfront_invalidation.py
        ├── docker_build_push.py
        ├── docker_compose_integration.py
        ├── env_file_generator.py
        ├── npm_build.py
        ├── sam_deploy.py
        └── test_*.py                 # Tests for each hook
```

## 📖 Detailed Usage Examples

### Example 1: Full Production Deployment
```
You: "Deploy the application to production using runway"

Claude (using runway-deploy agent):
1. 🔍 Validates runway.yml configuration
2. ⚠️  Warns about production deployment
3. 💡 Suggests running plan first: runway plan --deploy-environment prod
4. 🎯 Asks for confirmation
5. 🚀 Executes: runway deploy --deploy-environment prod
6. 📊 Monitors deployment progress
7. ✅ Executes post-deployment hooks
8. 📋 Provides deployment summary
```

### Example 2: Local Development Setup
```
You: "I want to test runway configurations locally"

Claude (using runway-local-dev agent):
1. 📁 Creates docker-compose.yml with LocalStack
2. 🔧 Configures runway.local.yml
3. 🐳 Starts Docker services
4. ⏳ Waits for services to be ready
5. 📋 Provides connection details
6. 💡 Shows usage examples
```

### Example 3: Hook Creation
```
You: "Create a hook that invalidates CloudFront cache after deployment"

Claude (using runway-create-hook agent):
1. ❓ Asks about hook requirements
2. 📝 Generates hook scaffolding
3. 🧪 Creates test file
4. ✅ Adds validation script
5. 📖 Generates documentation
6. 💡 Shows usage in runway.yml
```

### Example 4: Validation Workflow
```
You: /runway validate

Claude:
🔍 Runway Validation
━━━━━━━━━━━━━━━━━━━

📋 Validating configuration...
✅ Found: runway.yml
✅ Valid YAML syntax
✅ 2 deployment(s) configured

🔧 Validating hooks...
📁 Found 4 hook file(s)
✅ All hooks validated

✅ Ready for deployment!
```

### Example 5: MCP-Enhanced Template Validation
```
You: "Validate my CloudFormation template before deploying with runway"

Claude (using runway-deploy agent + cfn-mcp-server):
1. 📄 Reads CloudFormation template
2. 🔍 Uses cfn-lint via MCP to validate
3. ⚠️  Identifies issues:
   - Security group allows 0.0.0.0/0 ingress
   - Missing DeletionPolicy on RDS instance
   - Hard-coded AMI ID (region-specific)
4. 💡 Provides recommendations
5. ✅ Offers to fix issues before deployment
6. 🚀 Proceeds with runway deployment once fixed
```

### Example 6: Terraform Configuration Analysis
```
You: "Check my Terraform config before runway deploy"

Claude (using runway-deploy agent + terraform-mcp-server):
1. 📄 Scans Terraform .tf files
2. 🔍 Validates configuration syntax
3. 📊 Analyzes resource dependencies
4. ⚠️  Identifies potential issues:
   - Provider version constraints missing
   - Unused variables declared
   - Resource naming inconsistencies
5. 💡 Suggests improvements
6. ✅ Validates state compatibility
7. 🚀 Executes runway deployment
```

## 🎯 Best Practices

1. **Always validate before deploying**
   - Use `/runway validate` or let PreToolUse hook auto-validate
   - Fix any warnings before production deployments

2. **Test locally first**
   - Use runway-local-dev agent to set up LocalStack
   - Test configurations and hooks locally
   - Deploy to dev/staging before production

3. **Use agents for complex tasks**
   - Let agents handle multi-step workflows
   - Agents provide better error handling and guidance
   - Agents follow best practices automatically

4. **Create reusable hooks**
   - Use runway-create-hook agent for scaffolding
   - Follow established patterns from examples
   - Include tests and validation

5. **Environment isolation**
   - Use separate AWS accounts when possible
   - Tag resources appropriately
   - Use environment-specific configurations

## 🔧 Troubleshooting

### Issue: Configuration validation fails
```bash
# Check configuration
/runway validate config

# Or use agent for detailed analysis
"Validate my runway configuration and explain any issues"
```

### Issue: Hook not working
```bash
# Validate hooks
/runway validate hooks

# Or use specialized agent
"Validate my custom runway hooks and show me what's wrong"
```

### Issue: Local development not starting
```bash
# Use agent for help
"Help me troubleshoot my runway local development environment"

# Agent will check:
# - Docker status
# - Service logs
# - Port conflicts
# - Configuration issues
```

## 📚 Additional Resources

- **Agent Documentation**: See individual agent files in `agents/`
- **Hook Examples**: See `examples/hooks/` for reference implementations
- **Runway Docs**: https://docs.onica.com/projects/runway/
- **CFNgin Hooks**: https://docs.onica.com/projects/runway/en/latest/cfngin/hooks.html

## 🆘 Getting Help

Ask Claude for help with any runway task:

```
"How do I deploy to production safely?"
"Show me how to create a custom hook"
"Help me set up local development"
"Validate my runway configuration"
"What hooks are available?"
```

The skill's agents and commands will automatically activate based on your request!
