---
name: skill-creator
description: Guide for creating effective skills. This skill should be used when users want to create a new skill (or update an existing skill) that extends Claude's capabilities with specialized knowledge, workflows, or tool integrations.
license: Complete terms in LICENSE.txt
---

# Skill Creator

## Purpose

This skill provides guidance for creating modular, self-contained packages that extend Claude's capabilities. Skills transform Claude into specialized agents equipped with procedural knowledge, workflows, tool integrations, and domain expertise bundled with reusable resources.

## When to Use This Skill

Use this skill when users want to build new skills or improve existing ones. A skill is appropriate when the task involves creating "onboarding guides" for specific domains—packaging specialized knowledge, multi-step procedures, tool instructions, or company-specific logic that Claude can reference repeatedly.

## How to Use This Skill

Follow the six-step skill creation process sequentially:

1. **Understand with Examples** - Gather concrete use cases showing how the skill will be used
2. **Plan Contents** - Identify reusable scripts, references, and assets needed
3. **Initialize** - Run `python scripts/init_skill.py <skill-name> --path <output-directory>` to generate the template structure
4. **Edit** - Develop bundled resources first, then complete SKILL.md using imperative language
5. **Package** - Run `python scripts/package_skill.py <path/to/skill-folder>` to validate and distribute
6. **Iterate** - Refine based on real-world usage feedback

Focus SKILL.md on essential procedures while moving detailed information to `references/` files. Include scripts for repeated code, assets for templates, and references for documentation or schemas.

## Skill Structure

A skill directory should follow this structure:

```
my-skill/
├── SKILL.md           # Main skill file (required)
├── scripts/           # Executable code (optional)
├── references/        # Documentation for context (optional)
└── assets/            # Templates, images, etc. (optional)
```

## SKILL.md Format

Every SKILL.md must start with YAML frontmatter:

```yaml
---
name: skill-name-in-hyphen-case
description: Clear explanation of what the skill does and when to use it.
---
```

### Naming Requirements
- Hyphen-case identifier (e.g., 'data-analyzer')
- Lowercase letters, digits, and hyphens only
- Max 40 characters
- Must match directory name exactly

## Common Skill Patterns

### 1. Workflow-Based (sequential processes)
```markdown
## Overview
## Workflow Decision Tree
## Step 1
## Step 2...
```

### 2. Task-Based (tool collections)
```markdown
## Overview
## Quick Start
## Task Category 1
## Task Category 2...
```

### 3. Reference/Guidelines (standards)
```markdown
## Overview
## Guidelines
## Specifications
## Usage...
```

### 4. Capabilities-Based (integrated systems)
```markdown
## Overview
## Core Capabilities
### 1. Feature
### 2. Feature...
```

## Resource Directory Types

### scripts/
Executable code (Python/Bash) for automation. Scripts may be executed without loading into context.

### references/
Documentation loaded into context to inform Claude's decisions. Good for API references, schemas, detailed guides.

### assets/
Files used in output (templates, images, fonts). NOT loaded into context.

## Scripts

This skill includes helper scripts in the `scripts/` directory:

- **init_skill.py** - Initialize a new skill with template structure
- **package_skill.py** - Validate and package a skill into a zip file
- **quick_validate.py** - Validate a skill's structure and frontmatter

### Usage Examples

```bash
# Initialize a new skill
python .claude/skills/skill-creator/scripts/init_skill.py my-new-skill --path .claude/skills

# Validate a skill
python .claude/skills/skill-creator/scripts/quick_validate.py .claude/skills/my-new-skill

# Package a skill for distribution
python .claude/skills/skill-creator/scripts/package_skill.py .claude/skills/my-new-skill ./dist
```

## Best Practices

1. **Keep SKILL.md focused** - Move detailed docs to references/
2. **Use imperative language** - "Run the script" not "You should run the script"
3. **Include concrete examples** - Show realistic user requests and responses
4. **Validate before shipping** - Run quick_validate.py to catch issues
5. **Delete unused directories** - Not every skill needs scripts/, references/, and assets/
