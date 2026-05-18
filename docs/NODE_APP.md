# Node.js App — Build & Deploy Guide

## What this app does

Express 4.x application that exposes two REST endpoints.  Each request causes
Winston to emit log messages containing synthetic SSNs, emails, and phone
numbers.  The EDOT Node agent (auto-injected by the cluster) captures these log
records and ships them to the OTel Collector via OTLP.

| Endpoint | Method | What it logs |
|----------|--------|--------------|
| `/api/customer/:id` | GET | `Retrieving customer record for id=…, SSN: DDD-DD-DDDD` |
| `/api/customer/enroll` | POST | Full enrollment record with SSN, email, phone |
| `/health` | GET | Kubernetes liveness probe (no PII) |
| `/ready` | GET | Kubernetes readiness probe (no PII) |

---

## 1. Build & run locally

**Requirements:** Node.js 20 LTS, npm 10+

```bash
cd apps/node-app

# Install dependencies
npm ci

# Start (logs to stdout, no OTEL agent)
npm start

# Test requests
curl http://localhost:8080/api/customer/cust-test
curl -X POST http://localhost:8080/api/customer/enroll \
  -H 'Content-Type: application/json' \
  -d '{"customerId":"c1","firstName":"Alice","lastName":"Smith","ssn":"123-45-6789","email":"alice@example.com","phoneNumber":"555-123-4567"}'

# Dev mode with auto-reload
npm run dev
```

---

## 2. Build Docker image locally

```bash
cd apps/node-app

# Build
docker build -t node-datamask-app:local .

# Run locally
docker run --rm -p 8080:8080 \
  -e OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318 \
  -e OTEL_SERVICE_NAME=node-datamask-app \
  -e OTEL_LOGS_EXPORTER=otlp \
  -e OTEL_TRACES_EXPORTER=otlp \
  -e OTEL_METRICS_EXPORTER=otlp \
  -e OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf \
  node-datamask-app:local

# Verify health
curl http://localhost:8080/health
```

---

## 3. Build & push to ACR (manual)

```bash
# Variables — replace with your values
CONTAINER_REGISTRY="myacr.azurecr.io"
IMAGE_TAG="$(git rev-parse --short HEAD)"

cd apps/node-app

az acr login --name "${CONTAINER_REGISTRY%%.*}"

docker build -t "${CONTAINER_REGISTRY}/node-datamask-app:${IMAGE_TAG}" .
docker push   "${CONTAINER_REGISTRY}/node-datamask-app:${IMAGE_TAG}"
```

The AzDO pipeline (`pipelines/azure-pipelines-node.yml`) automates this on every push
to `main` or `otel-col-datamask`.

---

## 4. Deploy to AKS with Helm

**Prerequisites:** collector already deployed (see `docs/COLLECTOR.md`), `poc` namespace exists.

```bash
# Variables
CONTAINER_REGISTRY="myacr.azurecr.io"
IMAGE_TAG="<build-id-from-pipeline>"   # or: $(git rev-parse --short HEAD)

helm upgrade --install node-datamask-app \
  apps/node-app/helm/node-datamask-app \
  --namespace poc \
  --create-namespace \
  --set image.repository="${CONTAINER_REGISTRY}/node-datamask-app" \
  --set image.tag="${IMAGE_TAG}" \
  --set otel.endpoint="http://edot-collector-opentelemetry-collector.observability.svc.cluster.local:4318" \
  --wait
```

Override the otel block if EDOT auto-injection is already active:

```bash
helm upgrade --install node-datamask-app \
  apps/node-app/helm/node-datamask-app \
  --namespace poc \
  --set image.repository="${CONTAINER_REGISTRY}/node-datamask-app" \
  --set image.tag="${IMAGE_TAG}" \
  --set otel.enabled=false \
  --wait
```

---

## 5. Verify in-cluster

```bash
# Check pod is Running
kubectl get pods -n poc -l app.kubernetes.io/name=node-datamask-app

# Stream app logs — confirm raw SSN appears here (pre-masking)
kubectl logs -l app.kubernetes.io/name=node-datamask-app -n poc -f | grep SSN

# Port-forward and send a test request
kubectl port-forward svc/node-datamask-app 8081:80 -n poc
curl http://localhost:8081/api/customer/cust-123

# Check collector logs for [REDACTED-SSN]
kubectl logs -l app.kubernetes.io/name=opentelemetry-collector \
  -n observability -f | grep REDACTED
```

---

## 6. Helm values reference

Key overridable values in `apps/node-app/helm/node-datamask-app/values.yaml`:

| Value | Default | Description |
|-------|---------|-------------|
| `image.repository` | `""` | Full ACR image path |
| `image.tag` | `latest` | Image tag — use pipeline BuildId |
| `replicaCount` | `1` | Number of pod replicas |
| `otel.enabled` | `true` | Set false if EDOT operator injects env vars |
| `otel.endpoint` | `http://edot-collector-opentelemetry-collector:4318` | Collector OTLP HTTP endpoint |
| `otel.serviceName` | `node-datamask-app` | Service name in telemetry |
| `otel.environment` | `poc` | `deployment.environment` resource attribute |
| `resources.requests.memory` | `128Mi` | Pod memory request |
| `resources.limits.memory` | `256Mi` | Pod memory limit |

---

## 7. Uninstall

```bash
helm uninstall node-datamask-app --namespace poc
```
