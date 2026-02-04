# Deep Verify Test Corpus

This directory contains the labeled test corpus for the Deep Verify benchmarking system.

## Structure

```
corpus/
├── README.md                 # This file
├── manifest.yaml             # Auto-generated corpus metadata
├── manifest.py               # CorpusManifest dataclass
├── artifacts/                # Raw artifact files
│   ├── go/                   # Go code artifacts
│   ├── python/               # Python code artifacts
│   └── specs/                # Story specification artifacts
├── labels/                   # Label files (YAML)
│   └── {artifact_id}.yaml    # Expected domains, findings, false_positives
└── golden/                   # Golden test suite (10 artifacts)
    └── {artifact_id}.yaml    # Exact expected output
```

## Label Format

Each label file follows this schema:

```yaml
artifact_id: "dv-001"           # Unique identifier (dv-{NNN})
source: "bmad-assist/story-X-Y" or "synthetic"
artifact_type: "code"           # code | spec
language: "go"                  # go | python | typescript | javascript | rust | java | ruby | null
content_file: "artifacts/go/dv-001.go"

# Expected domains (ground truth)
expected_domains:
  - domain: "concurrency"
    confidence: 0.9
  - domain: "api"
    confidence: 0.8

# Expected findings (true positives)
expected_findings:
  - pattern_id: "CC-004"
    severity: "critical"
    line_number: 42
    quote: "if len(buf) > 0 { buf = append(buf, item) }"

# Known false positives (should NOT be flagged)
known_false_positives:
  - pattern_id: "CC-001"
    reason: "False positive - mutex protects access"
    line_number: 55

# Metadata for analysis
metadata:
  lines_of_code: 150
  complexity: "medium"
  has_race_condition: true
```

## Golden Test Format

Golden tests have exact expected verdicts:

```yaml
artifact_id: "golden-01"
content_file: "artifacts/go/golden-01.go"

expected_verdict:
  decision: "REJECT"
  score: 7.5
  findings:
    - id: "F1"
      severity: "critical"
      title: "Check-then-act race condition"
      method_id: "#153"
      pattern_id: "CC-004"
      domain: "concurrency"
      evidence:
        - quote: "if len(buf) > 0 { buf = append(buf, item) }"
          line_number: 42
  domains_detected:
    - domain: "concurrency"
      confidence: 0.9
  methods_executed: ["#153", "#154", "#155"]

tolerance:
  score: 0.1
  confidence: 0.05
```

## Adding New Artifacts

1. Add artifact file to appropriate `artifacts/{language}/` directory
2. Create label file in `labels/` directory
3. Run `python -m bmad_assist.deep_verify.metrics --regenerate-manifest`
4. Run benchmarks to validate: `python -m bmad_assist.deep_verify.metrics`

## Running Benchmarks

```bash
# Run full benchmark
python -m bmad_assist.deep_verify.metrics

# Run only golden tests
python -m bmad_assist.deep_verify.metrics --golden-only

# Filter by language
python -m bmad_assist.deep_verify.metrics --filter language=python

# Output to file
python -m bmad_assist.deep_verify.metrics --output report.json --format json
```

## Metrics Targets

| Metric | Target |
|--------|--------|
| Domain Detection Accuracy | >90% |
| CRITICAL False Positive Rate | <1% |
| ERROR False Positive Rate | <5% |
| WARNING False Positive Rate | <15% |
