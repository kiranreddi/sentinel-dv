# Detail Tools

Get comprehensive details about specific verification artifacts.

## tests.get

Retrieve complete test case information.

### Purpose
Get the indexed execution record for one test. Failure and artifact evidence are queried through their dedicated tools.

### Input Schema

```python
class TestsGetInput(BaseModel):
    test_id: str
```

### Output Schema

```python
class TestsGetOutput(BaseModel):
    schema_version: str = "1.0.0"
    item: TestCase

class TestCase(BaseModel):
    test_id: str
    test_id_full: str
    run_id: str
    framework: str
    name: str
    seed: int | None
    status: str
    duration_ms: int | None
    sim_vendor: str | None
    sim_version: str | None
    dut_top: str | None
    created_at: str
```

### Example

**Query**:
```json
{
  "test_id": "T20260125_143000_axi_burst_test"
}
```

**Response**:
```json
{
  "schema_version": "1.0.0",
  "item": {
    "test_id": "T20260125_143000_axi_burst_test",
    "test_id_full": "T20260125_143000_axi_burst_test",
    "run_id": "R20260125_143000",
    "framework": "uvm",
    "name": "axi_burst_test",
    "status": "fail",
    "seed": 42,
    "duration_ms": 15420,
    "sim_vendor": "vcs",
    "sim_version": "T-2025.06",
    "dut_top": "axi4_dut",
    "created_at": "2026-01-25T14:35:20Z"
  }
}
```

Use `failures.list(include_evidence=true)`, `coverage.summary(include_evidence=true)`,
and `wave.summary` for evidence and artifact-backed analysis.

---

## tests.topology

Retrieve test execution topology (sequences, components, phases).

### Purpose
Understand test structure, UVM component hierarchy, and execution flow.

### Input Schema

```python
class TestsTopologyInput(BaseModel):
    test_id: str
```

### Output Schema

```python
class TestsTopologyOutput(BaseModel):
    schema_version: str = "1.0.0"
    item: TestTopology

class TestTopology(BaseModel):
    test_id: str
    sequences: list[SequenceInfo]
    components: list[ComponentInfo]
    phases: list[PhaseInfo]

class SequenceInfo(BaseModel):
    name: str
    type: str
    parent: str | None

class ComponentInfo(BaseModel):
    name: str
    type: str
    parent: str | None

class PhaseInfo(BaseModel):
    name: str
    start_time_ns: int | None
    end_time_ns: int | None
```

### Example

**Query**:
```json
{
  "test_id": "T20260125_143000_axi_burst_test"
}
```

**Response**:
```json
{
  "schema_version": "1.0.0",
  "item": {
    "test_id": "T20260125_143000_axi_burst_test",
    "sequences": [
      {
        "name": "axi_write_burst_seq",
        "type": "axi_base_seq",
        "parent": "axi_virtual_seq"
      },
      {
        "name": "axi_read_burst_seq",
        "type": "axi_base_seq",
        "parent": "axi_virtual_seq"
      }
    ],
    "components": [
      {
        "name": "uvm_test_top",
        "type": "axi_burst_test",
        "parent": null
      },
      {
        "name": "env",
        "type": "axi_env",
        "parent": "uvm_test_top"
      },
      {
        "name": "axi_agent",
        "type": "axi_master_agent",
        "parent": "env"
      },
      {
        "name": "monitor",
        "type": "axi_monitor",
        "parent": "axi_agent"
      }
    ],
    "phases": [
      {
        "name": "build_phase",
        "start_time_ns": 0,
        "end_time_ns": 100
      },
      {
        "name": "connect_phase",
        "start_time_ns": 100,
        "end_time_ns": 150
      },
      {
        "name": "run_phase",
        "start_time_ns": 150,
        "end_time_ns": 15420000
      }
    ]
  }
}
```

---

## assertions.get

Get comprehensive assertion definition and runtime information.

### Purpose
View assertion details including intent, severity, source location, and firing history.

### Input Schema

```python
class AssertionsGetInput(BaseModel):
    name: str
    scope: str
```

### Output Schema

```python
class AssertionsGetOutput(BaseModel):
    schema_version: str = "1.0.0"
    item: AssertionDetail

class AssertionDetail(BaseModel):
    name: str
    scope: str
    file: str | None
    line: int | None
    protocol: str | None
    category: str
    severity: str
    intent: str
    description: str | None
    tags: list[str]
    total_firings: int
    tests_affected: list[str]
```

### Example

**Query**:
```json
{
  "name": "axi_awvalid_awready_check",
  "scope": "axi_master_if"
}
```

**Response**:
```json
{
  "schema_version": "1.0.0",
  "item": {
    "name": "axi_awvalid_awready_check",
    "scope": "axi_master_if",
    "file": "rtl/axi_master_if.sv",
    "line": 145,
    "protocol": "AXI4",
    "category": "protocol",
    "severity": "error",
    "intent": "AWVALID must remain high until AWREADY asserted",
    "description": "Once AWVALID is asserted, it must remain high until the corresponding AWREADY is asserted in the same cycle (handshake). This is a fundamental AXI4 protocol requirement.",
    "tags": ["handshake", "axi4", "write-channel"],
    "total_firings": 12,
    "tests_affected": [
      "T20260125_143000_axi_burst_test",
      "T20260125_143000_axi_protocol_test",
      "T20260124_091500_axi_stress_test"
    ]
  }
}
```

---

## Common Patterns

### Evidence References

Tests reference external artifacts using `EvidenceRef`:

```python
class EvidenceRef(BaseModel):
    type: str  # "log" | "waveform" | "coverage" | "assertion" | "uvm_error"
    path: str
    time_ns: int | None  # For failures/assertions
```

**Use Cases**:

1. **Log Files**
   ```json
   {
     "type": "log",
     "path": "artifacts/R20260125_143000/test/run.log"
   }
   ```

2. **Waveforms**
   ```json
   {
     "type": "waveform",
     "path": "artifacts/R20260125_143000/test/waves.vcd"
   }
   ```

3. **Coverage**
   ```json
   {
     "type": "coverage",
     "path": "artifacts/R20260125_143000/test/coverage.xml"
   }
   ```

4. **Assertion Failures**
   ```json
   {
     "type": "assertion",
     "path": "axi_master_if.axi_awvalid_awready_check",
     "time_ns": 12450
   }
   ```

### Test Configuration

The `config` field captures test parameters:

```json
{
  "seed": 42,
  "verbosity": "UVM_MEDIUM",
  "timeout_ns": 1000000,
  "plusargs": {
    "+UVM_TESTNAME": "axi_burst_test",
    "+UVM_VERBOSITY": "UVM_MEDIUM"
  }
}
```

### Topology Hierarchies

Component and sequence hierarchies use parent references:

```json
{
  "name": "monitor",
  "type": "axi_monitor",
  "parent": "axi_agent"
}
```

Build the full path by traversing parents:
```
uvm_test_top.env.axi_agent.monitor
```

### Phase Timing

UVM phases have optional timing information:

```json
{
  "name": "run_phase",
  "start_time_ns": 150,
  "end_time_ns": 15420000
}
```

Duration: `end_time_ns - start_time_ns = 15419850 ns`

## Error Handling

### Test Not Found

**Query**:
```json
{"test_id": "nonexistent"}
```

**Response**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Test 'nonexistent' not found"
  }
}
```

### Assertion Not Found

**Query**:
```json
{"name": "unknown_check", "scope": "unknown_scope"}
```

**Response**:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Assertion 'unknown_check' in scope 'unknown_scope' not found"
  }
}
```

## Best Practices

1. **Cache Test Details**
   ```python
   # ✅ Good - single query
   test = client.tests.get(test_id="T20260125_143000_axi_burst_test")
   
   # ❌ Bad - multiple queries
   for test_id in test_ids:
       test = client.tests.get(test_id=test_id)
   ```

2. **Use Topology for Debugging**
   ```python
   # Get test topology to understand structure
   topology = client.tests.topology(test_id="...")
   
   # Find component in hierarchy
   monitor = next(c for c in topology.components if c.type == "axi_monitor")
   ```

3. **Follow Evidence References**
   ```python
   # Get test with failure references
   test = client.tests.get(test_id="...")
   
   # Investigate each failure
   for failure_ref in test.failure_refs:
       if failure_ref.type == "assertion":
           assertion = client.assertions.get(
               name=failure_ref.path.split(".")[-1],
               scope=".".join(failure_ref.path.split(".")[:-1])
           )
   ```

## Next Steps

- [Analysis Tools →](analysis.md) - Analyze failure patterns
- [Regression Tools →](regression.md) - Compare test results
- [Discovery Tools →](discovery.md) - Find related tests
