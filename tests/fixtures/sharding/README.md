# Sharding Test Fixtures

Pre-built fixtures for testing sharded documentation support (Story standalone-02).

## Directory Structure

```
sharding/
├── epics-valid/           # Happy path: epics without index.md (numeric sort)
│   ├── epic-1-foundation.md
│   ├── epic-2-integration.md
│   └── epic-10-final.md   # Tests numeric sort (1, 2, 10 not 1, 10, 2)
│
├── epics-with-index/      # Index-guided loading with orphan file
│   ├── index.md           # Custom order: epic-2 before epic-1
│   ├── epic-1-foundation.md
│   ├── epic-2-integration.md
│   └── epic-3-orphan.md   # NOT in index - tests orphan handling
│
├── epics-empty/           # Edge case: empty directory
│   └── .gitkeep
│
├── epics-duplicate/       # Edge case: duplicate epic_id
│   ├── epic-1-first.md    # epic_id: 1
│   └── epic-1-second.md   # epic_id: 1 (DUPLICATE!)
│
├── epics-malformed/       # Edge case: invalid files
│   ├── epic-1-valid.md
│   ├── epic-2-no-frontmatter.md  # No YAML frontmatter
│   ├── epic-3-broken-yaml.md     # Invalid YAML syntax
│   └── not-an-epic.txt           # Non-.md file (should be ignored)
│
├── architecture-valid/    # Happy path: architecture (alphabetic sort)
│   ├── index.md
│   ├── core-decisions.md
│   ├── implementation-patterns.md
│   └── project-context.md
│
├── prd-valid/             # Happy path: PRD (alphabetic sort)
│   ├── index.md
│   ├── requirements.md
│   └── user-stories.md
│
├── ux-no-index/           # UX without index.md (alphabetic fallback)
│   ├── design-system.md   # Sorted alphabetically
│   └── wireframes.md
│
├── mixed-project/         # Mixed: some sharded, some single-file
│   ├── epics/
│   │   └── epic-1-only.md
│   ├── architecture.md    # Single file (NOT sharded)
│   └── prd.md             # Single file (NOT sharded)
│
└── security-traversal/    # Security: path traversal attempts
    ├── index.md           # Contains ../../../etc/passwd references
    └── legit.md           # Legitimate file
```

## Test Scenarios

### AC2, AC10-12: Happy Path Loading
- `epics-valid/` → Load 3 epics, sorted: 1, 2, 10 (numeric)
- `architecture-valid/` → Load 3 files, order from index.md
- `prd-valid/` → Load 2 files, order from index.md
- `ux-no-index/` → Load 2 files, alphabetic: design-system, wireframes

### AC3: Index-Guided Loading
- `epics-with-index/` → Custom order: epic-2 loaded BEFORE epic-1
- `epics-with-index/epic-3-orphan.md` → Orphan file handling

### AC7: Error Handling
- `epics-empty/` → Empty directory → empty result, warning logged
- `epics-duplicate/` → Duplicate epic_id → DuplicateEpicError
- `epics-malformed/` → Graceful handling of invalid files

### AC8: Security
- `security-traversal/` → Path traversal attempts → SecurityError

### AC9: Precedence (Single > Sharded)
- `mixed-project/` → architecture.md (single) takes precedence over architecture/ (dir)

### AC13: Doc-Type Specific Sorting
- `epics-valid/` → Numeric: 1, 2, 10
- `architecture-valid/` → Alphabetic: core-decisions, implementation-patterns, project-context

## Expected Results

| Fixture | Doc Type | Expected Order | Special |
|---------|----------|----------------|---------|
| epics-valid | epics | 1, 2, 10 | Numeric sort |
| epics-with-index | epics | 2, 1, 3 | Index order + orphan |
| architecture-valid | architecture | index, core-decisions, impl-patterns, project-context | From index |
| ux-no-index | ux | design-system, wireframes | Alphabetic fallback |
