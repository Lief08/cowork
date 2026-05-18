# OTel Data Masking PoC — Setup Guide

## Overview

This repository proves out log-level data masking in an OpenTelemetry Collector against
log entries emitted by EDOT-instrumented Java and Node.js applications running on AKS.

The pipeline:

```
[Java/Node App]
  ↓ OTLP (EDOT auto-injection)
[EDOT Collector — transform/redact or transform/hash processor]
  ↓ masked OTLP
[Downstream endpoint]  +  [debug exporter → kubectl logs]
```

---

## Prerequisites

| Tool | Minimum version | Install |
|------|----------------|---------|
| `kubectl` | 1.28+ | https://kubernetes.io/docs/tasks/tools/ |
| `helm` | 3.13+ | https://helm.sh/docs/intro/install/ |
| `k6` | 0.50+ | `brew install k6` / https://k6.io/docs/get-started/installation/ |
| Docker | 24+ | https://docs.docker.com/engine/install/ |
| Java JDK | 17 | `brew install openjdk@17` / https://adoptium.net |
| Maven | 3.9+ | `brew install maven` |
| Node.js | 20 LTS | `brew install node` / https://nodejs.org |
| Azure CLI | 2.55+ | `brew install azure-cli` |

Verify cluster access:
```bash
kubectl cluster-info
kubectl get nodes
```

---

## Repository structure

```
cowork/
├── apps/
│   ├── java-app/               Spring Boot app + Dockerfile + Helm chart
│   └── node-app/               Express app + Dockerfile + Helm chart
├── collector/
│   └── helm/values.yaml        EDOT Collector Helm values (masking pipelines)
├── pipelines/
│   ├── azure-pipelines-java.yml
│   └── azure-pipelines-node.yml
├── load-test/
│   └── k6-load-test.js
└── docs/
    ├── SETUP.md                (this file)
    ├── JAVA_APP.md
    ├── NODE_APP.md
    └── COLLECTOR.md
```

---

## Deploy order

Always deploy the collector first so it is ready to receive telemetry when the apps start.

```
1. EDOT Collector   →  see docs/COLLECTOR.md
2. Java app         →  see docs/JAVA_APP.md
3. Node.js app      →  see docs/NODE_APP.md
4. Load test        →  load-test/k6-load-test.js
```

---

## Namespace conventions

| Namespace | Contents |
|-----------|----------|
| `observability` | EDOT Collector |
| `poc` | Demo apps |

Create them if they do not already exist:
```bash
kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
kubectl create namespace poc           --dry-run=client -o yaml | kubectl apply -f -
```

---

## ACR image pull secret

If your AKS cluster is not attached to the ACR via managed identity, create an image pull
secret in the `poc` namespace:

```bash
kubectl create secret docker-registry acr-pull-secret \
  --docker-server=<CONTAINER_REGISTRY> \
  --docker-username=<sp-client-id> \
  --docker-password=<sp-client-secret> \
  --namespace poc
```

Then add `imagePullSecrets` to the Helm values for each app:
```yaml
# apps/<app>/helm/<chart>/values.yaml
imagePullSecrets:
  - name: acr-pull-secret
```

---

## Key environment variable reference

All OTEL env vars are set in each app's Helm `values.yaml` under `otel:`.
If EDOT auto-injection is active via an `Instrumentation` CRD, those values
take precedence and the `otel.enabled: false` override can suppress duplicates.

| Variable | Purpose |
|----------|---------|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Collector HTTP endpoint, e.g. `http://edot-collector-opentelemetry-collector.observability.svc.cluster.local:4318` |
| `OTEL_EXPORTER_OTLP_PROTOCOL` | `http/protobuf` (preferred for sidecar-less deployments) |
| `OTEL_SERVICE_NAME` | Service name tag in all telemetry |
| `OTEL_LOGS_EXPORTER` | `otlp` |
| `OTEL_TRACES_EXPORTER` | `otlp` |
| `OTEL_METRICS_EXPORTER` | `otlp` |
| `OTEL_RESOURCE_ATTRIBUTES` | e.g. `deployment.environment=poc` |

---

## Quick verification commands

```bash
# Confirm collector is running
kubectl get pods -n observability

# Confirm apps are running
kubectl get pods -n poc

# Stream collector logs — look for [REDACTED-SSN] in log bodies
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector \
  -n observability -f | grep -i "SSN\|REDACTED\|pii"

# Confirm raw SSN appears in app pod logs (before masking)
kubectl logs -l app.kubernetes.io/name=java-datamask-app -n poc | grep SSN
kubectl logs -l app.kubernetes.io/name=node-datamask-app -n poc | grep SSN

# Run load test (port-forward first or use in-cluster addresses)
kubectl port-forward svc/java-datamask-app 8080:80 -n poc &
kubectl port-forward svc/node-datamask-app 8081:80 -n poc &
k6 run --env APP_BASE_URL=http://localhost:8080 \
       --env SECONDARY_BASE_URL=http://localhost:8081 \
       load-test/k6-load-test.js
```
