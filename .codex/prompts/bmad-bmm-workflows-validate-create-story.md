---
description: 'Validate story context using power-prompt templates. Usage: /validate-create-story [epic]-[story] [power-prompt-file]'
---

IT IS CRITICAL THAT YOU FOLLOW THIS COMMAND:

**Usage:**
```
/validate-create-story [epic]-[story] [power-prompt-file]
```

**Examples:**
```bash
# Multi-LLM validator (read-only)
/validate-create-story 14-3 power-prompts/python-cli/validate-story-multi.md

# Master synthesis (can modify files)
/validate-create-story 14-3 power-prompts/python-cli/validate-story-master.md
```

<steps CRITICAL="TRUE">
1. Parse the arguments:
   - First argument: `[epic]-[story]` → extract `epic_num` and `story_num`
   - Second argument: path to power-prompt template file

2. Verify the story file exists at:
   `_bmad-output/implementation-artifacts/stories/{epic_num}-{story_num}-*.md`

3. READ the power-prompt template file provided as second argument

4. Substitute variables in the power-prompt:
   - Replace `{{epic_num}}` with extracted epic number/id
   - Replace `{{story_num}}` with extracted story number

5. Execute the power-prompt instructions exactly as written

6. Save outputs to the location specified in the power-prompt
</steps>

**Power-Prompt Templates:**
- `power-prompts/python-cli/validate-story-multi.md` - Multi-LLM validation (NO file modifications)
- `power-prompts/python-cli/validate-story-master.md` - Master synthesis (CAN modify files)
