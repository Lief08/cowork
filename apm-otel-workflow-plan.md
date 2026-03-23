# APM Instrumentation Automation Workflow
## OpenTelemetry SDK Agent + Collector End-to-End Installation Plan

**Version:** 1.0  
**Date:** 2026-03-22  
**Status:** Planning / Iteration  
**Authors:** Observability Engineering

---

## 1. Purpose & Scope

This document defines the end-to-end automation workflow for instrumenting an existing Java runtime with OpenTelemetry. It covers the installation of the OpenTelemetry Java SDK Agent, the deployment and configuration of a local OpenTelemetry Collector, and the required configuration changes to the Java runtime itself.

There are two equally important goals:

1. **Operational clarity** — define every discrete task required to achieve full APM instrumentation from a clean state (server and runtime exist; no APM components present).
2. **Ownership delineation** — draw a hard, explicit boundary between the automation components, configuration objects, and operational responsibilities owned by **Observability Engineering (OE)** and those owned by **Platform Engineering (PE)**.

This document is the planning artifact from which the visual workflow diagram is derived. It should be iterated on before any automation is built.

---

## 2. Ownership Model

| Component | Owned By | Notes |
|---|---|---|
| OTel Collector binary + packaging | Observability Engineering | Version-pinned, artifact registry sourced |
| OTel Collector service installation | Observability Engineering | Systemd unit or equivalent |
| OTel Collector pipeline configuration | Observability Engineering | Receivers, processors, exporters |
| OTel Java Agent JAR | Observability Engineering | Version-pinned, artifact registry sourced |
| Agent configuration payload (env vars, JVM args) | Observability Engineering | Authored and packaged as handoff artifact |
| **Handoff Interface / Config Spec** | **Shared — formal artifact** | **OE authors, PE receives and validates** |
| Java runtime startup configuration | Platform Engineering | JVM args, startup scripts, service wrappers |
| Environment variable application to runtime | Platform Engineering | Applied per OE-authored manifest |
| Runtime restart / lifecycle | Platform Engineering | PE owns the runtime; OE does not touch it |
| Backup of runtime config (pre-change) | Platform Engineering | PE executes, OE defines requirements |
| Backup of Collector config (pre-change) | Observability Engineering | OE executes |
| Validation — agent load confirmation | Observability Engineering | OE confirms agent banner and telemetry flow |
| Validation — telemetry pipeline end-to-end | Observability Engineering | OE confirms Collector receipt and backend export |
| Validation — runtime availability and performance | Platform Engineering | PE confirms runtime health, logs, and baseline perf |
| Validation — smoke testing and regression | Application Development | AD confirms business functionality and no regressions |
| Rollback execution — agent/runtime | Platform Engineering | PE executes, OE authors the procedure |
| Rollback execution — Collector | Observability Engineering | OE executes |
| Escalation & incident filing | Shared | All three teams participate |

---

## 3. Pre-Conditions

The following conditions must be true before this workflow begins. Neither team is responsible for establishing these conditions as part of this workflow.

- Target server is provisioned and reachable
- Java runtime (JVM) is installed and the version is known
- Java application is deployed and capable of starting (runtime is in a known-good state)
- Network path from server to observability backend is confirmed (or a proxy/Collector chain is in place)
- Artifact registry is accessible from the target server (for pulling Collector binary and agent JAR)
- Both teams have agreed on: service name, environment label, Collector endpoint, and sampling configuration before automation begins
- Change window is defined, approved, and communicated to all three teams (OE, PE, AD) including start time, end time, and rollback time budget

**Pre-condition validation is a shared gate.** If any pre-condition is unmet, the workflow does not start.

---

## 4. Workstream A — Collector Installation (Observability Engineering)

This workstream runs in parallel with Workstream B. Both must complete before the Handoff Interface is engaged.

### 4.1 Backup Check

Before any installation begins, OE automation checks whether an existing Collector installation or configuration is present on the target server. If found:

- Archive the existing config file to a timestamped backup path (e.g., `/etc/otelcol/config.yaml.bak.<timestamp>`)
- Record the existing service state (running / stopped / absent)
- Do not stop or remove the existing service automatically; surface a warning and require operator confirmation to proceed

If no existing installation is found, proceed without backup.

### 4.2 Stage Collector Binary

- Pull the OTel Collector binary (Contrib distribution recommended) from the internal artifact registry
- Verify checksum against known-good hash
- Stage to a temporary working directory on the target server

### 4.3 Install as System Service

- Copy binary to installation path (e.g., `/usr/local/bin/otelcol`)
- Install systemd unit file (OE-maintained template)
- Do not start the service yet

**Automation owner:** OE  
**Config artifact:** systemd unit file (version-controlled in OE repository)

### 4.4 Configure Pipelines

- Write the Collector config file (`config.yaml`) from OE-maintained template, parameterized for this target
- Configuration includes:
  - **Receivers:** OTLP (gRPC and/or HTTP) on localhost
  - **Processors:** batch, memory limiter, resource detection
  - **Exporters:** OTLP/HTTP to observability backend (or next Collector hop)
  - **Service pipelines:** traces, metrics, logs (as applicable)
- Config is written before service start; no live reload at this step

### 4.5 Start and Health Check

- Enable and start the Collector service (`systemctl enable --now otelcol`)
- Poll the Collector's internal metrics endpoint (`http://localhost:8888/metrics`) until healthy or until timeout (default: 60 seconds)
- Verify OTLP receiver port is open and listening
- Log validation outcome; fail the workstream if health check does not pass within timeout

---

## 5. Workstream B — Agent Preparation (Observability Engineering)

This workstream runs in parallel with Workstream A. It produces the config manifest artifact that is the primary input to the Handoff Interface.

### 5.1 Stage Java Agent JAR

- Pull the OpenTelemetry Java Agent JAR (version-pinned) from the internal artifact registry
- Verify checksum
- Stage to a stable, well-known path on the target server (e.g., `/opt/otel/opentelemetry-javaagent.jar`)
- Set file permissions: readable by the runtime process user, not writable

### 5.2 Build Configuration Payload

OE automation builds the complete set of configuration inputs that PE will apply to the runtime. These are not applied by OE — they are packaged and handed off.

| Item | Value / Example |
|---|---|
| JVM argument | `-javaagent:/opt/otel/opentelemetry-javaagent.jar` |
| `OTEL_SERVICE_NAME` | `<service-name>` (agreed pre-condition) |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` (local Collector) |
| `OTEL_RESOURCE_ATTRIBUTES` | `deployment.environment=<env>,host.name=<hostname>` |
| `OTEL_TRACES_SAMPLER` | `parentbased_traceidratio` (or as agreed) |
| `OTEL_TRACES_SAMPLER_ARG` | `1.0` (or as agreed) |
| Additional `OTEL_*` vars | Per service-specific requirements |

### 5.3 Package Handoff Spec

- Serialize the configuration payload into a structured, human-readable artifact (e.g., a YAML or JSON manifest file)
- Include: agent JAR path, full JVM args string, all environment variable key-value pairs, Collector endpoint, and a checksum of the agent JAR
- Store the manifest at a known path accessible to both teams
- This artifact is the formal input to the Handoff Interface

---

## 6. Synchronization Gate

Both Workstream A and Workstream B must reach a successful completion state before the workflow advances. This is a hard gate — not a soft dependency.

**Gate conditions:**

- Collector is installed, configured, and health-check passing
- Agent JAR is staged and checksum-verified
- Handoff spec manifest is written and valid

If either workstream fails at the sync gate, the workflow halts. The failed workstream is retried or escalated. The passing workstream does not roll back at this point unless a full retry is initiated from the pre-conditions step.

---

## 7. Handoff Interface

The Handoff Interface is the formal boundary between OE and PE. It is the most important structural element of this workflow.

**What OE delivers to PE:**

- Path to the agent JAR on the target server
- Complete JVM argument string (ready to paste/inject into runtime config)
- Enumerated environment variables with values (the manifest from 5.3)
- Collector endpoint and port
- Expected behavior description (what PE should observe on successful restart)
- Rollback procedure document (authored by OE, executed by PE if needed)
- Backup requirements (what PE must capture before applying changes)

**Form of the handoff:** Teams should agree on a concrete mechanism — options include a pull request against the runtime's configuration repository, a ticket with structured fields, or a file drop to a shared path. The mechanism is less important than the fact that it is explicit, versioned, and auditable.

**PE accepts the handoff** by acknowledging receipt and confirming they have read and understood the manifest before proceeding.

---

## 8. Runtime Configuration (Platform Engineering)

PE owns this workstream entirely. OE does not execute any steps here. OE may observe (log tailing, monitoring) but does not control.

### 8.1 Backup Runtime Configuration

Before applying any changes, PE must capture the current state of the runtime configuration:

- Copy runtime startup script(s) / JVM args file to a timestamped backup (e.g., `/opt/app/startup.sh.bak.<timestamp>`)
- Export current environment variable state for the runtime process
- Record the backup path in the incident/change ticket
- Confirm backup is readable and complete before proceeding

**This backup is the source of truth for a Tier 1 rollback.**

### 8.2 Apply JVM Argument

- Add the `-javaagent` argument to the runtime's JVM argument chain
- This is typically applied in the startup script, a JVM options file (`jvm.options`, `JAVA_OPTS` env var, etc.) — PE knows the canonical location
- Do not apply partial arguments; the full `-javaagent:/path/to/opentelemetry-javaagent.jar` string must be present

### 8.3 Set Environment Variables

- Apply all `OTEL_*` environment variables from the OE-authored manifest
- Verify no existing `OTEL_*` variables conflict with the new values
- If conflicts are found, surface them to OE before proceeding — do not overwrite silently

### 8.4 Restart Runtime

- Perform a controlled restart of the Java runtime (not a kill; use the defined lifecycle mechanism)
- Monitor startup logs for JVM agent load confirmation before declaring the runtime healthy
- If the runtime fails to start, initiate Tier 1 Rollback immediately (do not attempt multiple restarts with agent flags present)

---

## 9. Validation Phase (Three-Team Responsibility)

Validation runs across three parallel tracks, each owned by a distinct team. All three tracks must pass before the workflow is considered complete. No single team's sign-off is sufficient on its own.

### Track 1 — Observability Engineering

OE validates that instrumentation is functioning correctly and telemetry is flowing end-to-end.

**9.1 Agent Load Confirmation**
- Inspect JVM startup logs for the OpenTelemetry Java Agent banner (logged at INFO on startup)
- Confirm the `-javaagent` argument appears in the running process command line
- **Owner:** OE

**9.2 Telemetry Reaching the Collector**
- Inspect Collector OTLP receiver logs for incoming span/metric/log data from the target service
- Verify data is arriving within 2–3 minutes after runtime startup
- Check Collector internal metrics (`otelcol_receiver_accepted_spans`, etc.) for non-zero values
- **Owner:** OE

**9.3 Collector Exporting to Backend**
- Verify Collector exporter logs show successful export to the observability backend
- Confirm data is visible in the backend UI (trace search, metrics explorer, etc.)
- **Owner:** OE

### Track 2 — Platform Engineering

PE validates that the runtime and host system remain healthy after the instrumented restart.

**9.4 Runtime Availability**
- Confirm the runtime process is running and responsive
- Verify any health endpoints the application exposes are returning healthy
- **Owner:** PE

**9.5 Application Log Review**
- Review application logs for unexpected errors, exceptions, or JVM failures introduced by the restart
- Specifically check for classloading conflicts or agent-related stack traces
- **Owner:** PE

**9.6 Performance Baseline Check**
- Confirm response times and resource utilization are within acceptable range relative to pre-change baseline
- Agent overhead should be observable but not disruptive — flag to OE if overhead is unexpectedly high
- **Owner:** PE

### Track 3 — Application Development

AD validates that business functionality is unaffected by the instrumented state of the runtime.

**9.7 Smoke Test Execution**
- Execute the defined smoke test suite against the instrumented runtime
- Critical path requests must complete successfully with no functional regressions
- **Owner:** AD

**9.8 Regression Verification**
- Run the automated regression suite against the instrumented runtime
- No new test failures may be introduced relative to the pre-change baseline
- **Owner:** AD

**9.9 Business Functionality Sign-off**
- AD team confirms all key business workflows are operational
- AD formally accepts the instrumented state of the application before the workflow closes
- **Owner:** AD

### 9.10 Validation Decision

All three tracks must pass. If any track fails, advance to the Rollback Strategy (Section 11) and identify the failure scope for triage. A failure in any single track is sufficient to trigger rollback — do not close the change record with partial validation.

---

## 10. Backup Strategy

### OE Backup (Workstream A, Step 4.1)

| Item | Backup Location | Retention |
|---|---|---|
| Existing Collector config (if present) | `/etc/otelcol/config.yaml.bak.<timestamp>` | 30 days |
| Existing systemd unit (if present) | `/etc/systemd/system/otelcol.service.bak.<timestamp>` | 30 days |
| Existing Collector binary (if present) | `/usr/local/bin/otelcol.bak.<timestamp>` | 30 days |

### PE Backup (Workstream C, Step 8.1)

| Item | Backup Location | Retention |
|---|---|---|
| Runtime startup script | `<script-path>.bak.<timestamp>` | 30 days |
| JVM options file (if separate) | `<options-file>.bak.<timestamp>` | 30 days |
| Exported environment variable snapshot | `/opt/backup/runtime-env.<timestamp>.txt` | 30 days |

**Backup naming convention:** `<original-filename>.bak.YYYYMMDD-HHMMSS`  
**Backup verification:** automation must confirm the backup file exists and is non-zero size before the workflow gate advances.

---

## 11. Rollback Strategy

### Rollback Triggers

Rollback is immediate upon failure of any validation track or any step in the PE runtime configuration workstream. There is no "attempt to fix in place" — rollback starts as soon as a failure is confirmed.

- Java runtime fails to start after applying agent arguments (immediate Tier 1)
- Any OE validation check fails within the agreed validation window
- Any PE validation check indicates runtime instability or performance degradation
- Any AD smoke or regression test fails against the instrumented runtime
- Collector fails health check and cannot recover within 60-second timeout

### Rollback Triage

Triage determines two things simultaneously: which rollback tier to execute, and which data collection scope to apply. Both begin immediately — triage is not a gate, it is a classification.

### Tier 1 — Agent / Runtime Rollback (PE Executes · Immediate)

**Execution:**

1. Stop the Java runtime (controlled shutdown — not kill)
2. Remove the `-javaagent` JVM argument from the runtime startup configuration
3. Unset all `OTEL_*` environment variables applied in Step 8.3
4. Restore the runtime startup script from the timestamped backup
5. Restart the runtime
6. Confirm the runtime starts cleanly with no agent log line present
7. Notify OE and AD of rollback completion

**Expected duration:** 5–15 minutes

**Data Collection — Tier 1:**

- JVM startup logs from the failed instrumented run (full, not truncated)
- Agent banner output or absence thereof
- Snapshot of `OTEL_*` environment variable state at time of failure
- `-javaagent` argument state from the running process command line
- Application error logs from the failure window
- AD test output and failure report (if failure was in AD track)

### Tier 2 — Collector Rollback (OE Executes · Immediate)

**Execution:**

1. Stop the Collector service (`systemctl stop otelcol`)
2. If config issue: restore `config.yaml` from backup and optionally restart to confirm recovery
3. If installation issue: remove service unit, binary, and config entirely; restore backups where available
4. Verify no orphaned Collector processes remain
5. Confirm the OTLP receiver port is no longer in use
6. Notify PE of rollback scope and status

**Expected duration:** 5–10 minutes

**Data Collection — Tier 2:**

- Collector service logs from the full instrumented window
- Config file state at time of failure (copy, not reference)
- Internal metrics endpoint output (`/metrics` scrape) captured at failure time
- Exporter error logs and receiver drop counts
- Collector process resource utilization at time of failure

### Tier 3 — Full Rollback (Both Teams · Immediate · PE First)

**Execution:**

1. PE executes Tier 1 immediately — runtime must be confirmed stable before OE proceeds
2. OE executes Tier 2 after PE confirms runtime is stable
3. Sequencing rationale: removing the agent before the Collector prevents OTLP export errors from further destabilizing the runtime during Collector teardown

**Data Collection — Tier 3:**

All Tier 1 and Tier 2 artifacts, plus full environment state snapshot, network path confirmation, and any request traces captured during the instrumented window.

### Root Cause Analysis (Always Required · Parallel Track)

RCA begins immediately when triage is complete — it does not wait for rollback to finish. Both activities run in parallel. RCA is not conditional; it is required regardless of failure scope or change window outcome.

The RCA track owns: preservation of all diagnostic artifacts, failure timeline reconstruction, identification of the specific failure point, and production of a written RCA document accepted by all three teams.

### Post-Rollback Verification (Shared)

1. Confirm target runtime is running and application is healthy
2. Confirm no orphaned `otelcol` processes remain
3. Confirm no `OTEL_*` environment variables remain in the runtime environment
4. Confirm no `-javaagent` argument is present in the running process command line
5. Confirm all diagnostic data is preserved and accessible to the RCA track

### Change Window Outcome

After post-rollback verification is complete, the outcome is determined by whether the rollback finished within the original change window.

**Within change window:** Close the change record as unsuccessful. No incident is required. The change outcome, rollback tier, and preliminary failure scope are documented in the change record.

**Beyond change window:** File an incident. The incident record is linked to the change record. Incident management is engaged and owns communication of extended impact.

### Retry Requirements

Retrying the workflow is not a decision made immediately after rollback. It is a separate process that requires all of the following before a new change can be scheduled:

1. RCA is formally complete and accepted by all three teams
2. The identified root cause has been corrected — in automation scripts, configuration templates, or process — and the correction has been peer-reviewed
3. A new change request has been raised, reviewed, and approved through the standard change management process
4. A new change window has been scheduled

The previous change artifacts (backup files, handoff manifest, diagnostic data) must be preserved and available for reference during the new change execution.

---

## 12. Open Questions for Iteration

1. **Change window definition** — What is the agreed change window duration, and what is the explicit rollback time budget within it? (e.g., 2-hour window with 45-minute rollback budget before incident is triggered)
2. **Handoff mechanism** — PR, ticket, file drop, or API call?
2. **Collector distribution** — Core vs. Contrib? Custom components required?
3. **Multi-instance scope** — Single server or fleet? Rollback complexity increases significantly at fleet scale.
4. **Runtime lifecycle mechanism** — systemd, init script, k8s pod restart, custom wrapper?
5. **Validation window** — Agreed timeout for telemetry to appear post-restart before rollback triggers?
6. **Sampling configuration** — Pre-condition agreement or configurable post-deployment?
7. **Secret management** — How are backend exporter credentials injected into Collector config?

---

*This document is a living planning artifact. Update it as decisions are made on the open questions above. The companion diagram (`apm-otel-workflow-detail.mermaid`) is derived from this document and should be kept in sync.*