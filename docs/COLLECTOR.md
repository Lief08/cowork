# EDOT Collector — Configuration & Masking Guide

## Overview

The OTel Collector acts as the ETL pipeline component: it receives OTLP telemetry
from the demo apps, applies OTTL (OpenTelemetry Transformation Language) transform
processors to mask PII in log record bodies, and forwards the sanitised data to the
downstream exporter.

Two masking strategies are implemented as separate, independently togglable pipelines:

| Pipeline | Processor | What it does |
|----------|-----------|--------------|
| `logs/redact` | `transform/redact` | Replaces PII with static placeholders — nothing persists |
| `logs/hash` | `transform/hash` | Same redaction + stores SHA256 of the original SSN as `pii.ssn.hashed` attribute for downstream correlation |

Only one logs pipeline should be active at a time during testing.

---

## Image choice

The Helm values default to `otel/opentelemetry-collector-contrib` because it is the
publicly versioned image guaranteed to include all required processors.

To use the EDOT (Elastic) image, override the image values:

```bash
helm upgrade --install edot-collector open-telemetry/opentelemetry-collector \
  --namespace observability \
  -f collector/helm/values.yaml \
  --set image.repository="docker.elastic.co/elastic-agent/elastic-agent" \
  --set image.tag="9.0.0"
```

The processor configuration in `values.yaml` is identical for both images since the
EDOT Collector is built on top of `collector-contrib`.

---

## Install

```bash
# Add the OTel Helm repo (once per workstation)
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Create namespace
kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -

# Deploy collector (Pipeline A: static redaction active by default)
helm upgrade --install edot-collector open-telemetry/opentelemetry-collector \
  --namespace observability \
  --create-namespace \
  -f collector/helm/values.yaml \
  --set 'extraEnvs[0].value=https://YOUR-APM-ENDPOINT:443' \
  --set 'extraEnvs[1].value=ApiKey YOUR-API-KEY' \
  --wait
```

To use a Kubernetes Secret for credentials instead of `--set` flags:

```bash
# Create the secret first
kubectl create secret generic edot-collector-downstream \
  --namespace observability \
  --from-literal=endpoint="https://YOUR-APM-ENDPOINT:443" \
  --from-literal=auth-header="ApiKey YOUR-API-KEY"

# Then update the extraEnvs block in values.yaml:
# extraEnvs:
#   - name: OTEL_DOWNSTREAM_ENDPOINT
#     valueFrom:
#       secretKeyRef:
#         name: edot-collector-downstream
#         key: endpoint
#   - name: OTEL_DOWNSTREAM_AUTH_HEADER
#     valueFrom:
#       secretKeyRef:
#         name: edot-collector-downstream
#         key: auth-header

helm upgrade edot-collector open-telemetry/opentelemetry-collector \
  --namespace observability \
  -f collector/helm/values.yaml \
  --wait
```

---

## Switch between masking strategies

Edit `collector/helm/values.yaml` — find the `service.pipelines` section and
comment/uncomment the desired pipeline, then re-run `helm upgrade`.

**Pipeline A (redact — default):**
```yaml
service:
  pipelines:
    logs/redact:
      receivers:  [otlp]
      processors: [memory_limiter, transform/redact, batch]
      exporters:  [debug, otlp/downstream]
    # logs/hash:
    #   ...
```

**Pipeline B (hash + redact):**
```yaml
service:
  pipelines:
    # logs/redact:
    #   ...
    logs/hash:
      receivers:  [otlp]
      processors: [memory_limiter, transform/hash, batch]
      exporters:  [debug, otlp/downstream]
```

Apply:
```bash
helm upgrade edot-collector open-telemetry/opentelemetry-collector \
  --namespace observability \
  -f collector/helm/values.yaml \
  --wait
```

---

## Verify masking (Pipeline A)

1. **Confirm raw PII in app logs** (before the collector sees it):
   ```bash
   kubectl logs -l app.kubernetes.io/name=java-datamask-app -n poc | grep -E "[0-9]{3}-[0-9]{2}-[0-9]{4}"
   # Expected: lines containing SSNs like  "SSN: 234-56-7890"
   ```

2. **Confirm masking in collector debug output:**
   ```bash
   kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -n observability -f \
     | grep -E "REDACTED|pii\."
   # Expected: log bodies containing [REDACTED-SSN] — no raw SSN digits
   ```

3. **Confirm no raw SSN reaches the collector debug output:**
   ```bash
   kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -n observability \
     | grep -E "[0-9]{3}-[0-9]{2}-[0-9]{4}"
   # Expected: zero matches
   ```

---

## Verify masking (Pipeline B — hash)

After switching to `logs/hash`:

```bash
# Confirm hash attribute is present
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -n observability -f \
  | grep "pii.ssn.hashed"
# Expected: lines containing a 64-character hex SHA256 digest

# Confirm pii.detected flag is set
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -n observability \
  | grep "pii.detected"
# Expected: lines containing  pii.detected: true

# Confirm log body is still redacted (no raw SSN)
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector -n observability \
  | grep -E "[0-9]{3}-[0-9]{2}-[0-9]{4}"
# Expected: zero matches
```

---

## OTTL processor reference

### `replace_pattern(body, regex, replacement)`

Replaces all substrings of the log record body matching the Go regex with the
replacement string.  Supports `$1`, `$2` capture group references in the replacement.

```yaml
- replace_pattern(body, "[0-9]{3}-[0-9]{2}-[0-9]{4}", "[REDACTED-SSN]")
```

### `IsMatch(body, regex)`

Returns `true` if the log body matches the regex.  Used as a `where` clause guard:

```yaml
- set(attributes["pii.detected"], true) where IsMatch(body, "[0-9]{3}-[0-9]{2}-[0-9]{4}")
```

### `ExtractPatterns(body, regex)`

Returns a `map[string]string` of named capture groups.  Requires Go named group syntax
`(?P<name>...)`:

```yaml
- set(attributes["_tmp_ssn"], ExtractPatterns(body, "(?P<ssn>[0-9]{3}-[0-9]{2}-[0-9]{4})")["ssn"])
```

### `SHA256(value)`

Returns a lowercase hex-encoded SHA256 digest of the input string.

- **Minimum version:** `collector-contrib` v0.98.0 / equivalent EDOT image
- **Fallback:** Replace `SHA256(...)` with `MD5(...)` for older images (MD5 is not
  cryptographically strong — use only when SHA256 is unavailable and the hash is for
  correlation only, not security)

---

## Structured log bodies

If your production apps emit JSON-structured log bodies rather than plain strings
(e.g. `{"message": "...", "ssn": "123-45-6789"}`), the OTTL target changes from
`body` to `body["ssn"]` (for a top-level key) or `body["nested"]["field"]`:

```yaml
# Redact a specific field in a structured log body
- set(body["ssn"], "[REDACTED-SSN]") where body["ssn"] != nil

# Or use replace_pattern on a nested string field
- replace_pattern(body["message"], "[0-9]{3}-[0-9]{2}-[0-9]{4}", "[REDACTED-SSN]")
```

The demo apps in this repo use plain-string log messages (the common default for
Spring Boot / Winston), so `body` targets the string directly.

---

## Uninstall

```bash
helm uninstall edot-collector --namespace observability
```
