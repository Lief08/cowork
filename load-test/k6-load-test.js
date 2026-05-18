/**
 * k6 Load Test — OTel Data Masking PoC
 *
 * Generates sustained traffic against the Java and/or Node.js demo apps so
 * their log records (containing synthetic SSNs) flow through the OTel
 * Collector's masking pipeline.
 *
 * Usage:
 *   # Against a single app (port-forwarded locally):
 *   k6 run load-test/k6-load-test.js
 *
 *   # Against a specific base URL:
 *   k6 run --env APP_BASE_URL=http://java-datamask-app.poc.svc.cluster.local load-test/k6-load-test.js
 *
 *   # Against both apps simultaneously, longer run:
 *   k6 run --env APP_BASE_URL=http://<java-svc> \
 *           --env SECONDARY_BASE_URL=http://<node-svc> \
 *           --duration 2m --vus 20 \
 *           load-test/k6-load-test.js
 *
 * Port-forward shortcuts (run in separate terminals before k6):
 *   kubectl port-forward svc/java-datamask-app 8080:80 -n poc
 *   kubectl port-forward svc/node-datamask-app 8081:80 -n poc
 *   # Then: APP_BASE_URL=http://localhost:8080
 *   #       SECONDARY_BASE_URL=http://localhost:8081
 *
 * Install k6: https://k6.io/docs/getting-started/installation/
 *   macOS:  brew install k6
 *   Linux:  https://k6.io/docs/getting-started/installation/#linux
 */

import http from 'k6/http';
import { check, sleep } from 'k6';

// ─── Target URLs ─────────────────────────────────────────────────────────────
// Primary target (defaults to localhost:8080 for local port-forward testing)
const BASE_URL = __ENV.APP_BASE_URL || 'http://localhost:8080';

// Optional secondary target (e.g. the other app).
// Leave blank to only hit the primary.
const SECONDARY_BASE_URL = __ENV.SECONDARY_BASE_URL || '';

// ─── Test configuration ───────────────────────────────────────────────────────
export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    // Less than 1% of requests should fail
    http_req_failed: ['rate<0.01'],
    // 95th percentile response time under 2 seconds
    http_req_duration: ['p(95)<2000'],
  },
};

// ─── Synthetic test data ──────────────────────────────────────────────────────
// These are NOT real SSNs. They are generated to match the SSN regex pattern
// (DDD-DD-DDDD) used by the OTel Collector masking processor.
const FAKE_SSNS = [
  '234-56-7890',
  '345-67-8901',
  '456-78-9012',
  '567-89-0123',
  '678-90-1234',
  '789-01-2345',
  '321-54-9876',
  '432-65-1098',
];

const CUSTOMER_IDS = [
  'cust-alpha',
  'cust-bravo',
  'cust-charlie',
  'cust-delta',
  'cust-echo',
];

const FIRST_NAMES = ['Alice', 'Bob', 'Carol', 'David', 'Eve'];
const LAST_NAMES  = ['Smith', 'Jones', 'Williams', 'Brown', 'Davis'];

function randomItem(arr) {
  return arr[Math.floor(Math.random() * arr.length)];
}

// ─── Request helpers ──────────────────────────────────────────────────────────
function doGetCustomer(baseUrl) {
  const id  = randomItem(CUSTOMER_IDS);
  const res = http.get(`${baseUrl}/api/customer/${id}`, {
    tags: { endpoint: 'GET /api/customer/:id' },
  });

  check(res, {
    'GET customer: status 200':     (r) => r.status === 200,
    'GET customer: has customerId': (r) => {
      try { return JSON.parse(r.body).customerId !== undefined; }
      catch (_) { return false; }
    },
  });
}

function doPostEnroll(baseUrl) {
  const ssn     = randomItem(FAKE_SSNS);
  const payload = JSON.stringify({
    customerId:  `cust-new-${Date.now()}`,
    firstName:   randomItem(FIRST_NAMES),
    lastName:    randomItem(LAST_NAMES),
    ssn:         ssn,
    email:       `test${Math.floor(Math.random() * 9999)}@example-poc.com`,
    phoneNumber: '555-123-4567',
  });

  const res = http.post(`${baseUrl}/api/customer/enroll`, payload, {
    headers: { 'Content-Type': 'application/json' },
    tags:    { endpoint: 'POST /api/customer/enroll' },
  });

  check(res, {
    'POST enroll: status 200':     (r) => r.status === 200,
    'POST enroll: has customerId': (r) => {
      try { return JSON.parse(r.body).customerId !== undefined; }
      catch (_) { return false; }
    },
  });
}

// ─── Default function (executed per VU per iteration) ─────────────────────────
export default function () {
  // Alternate between GET and POST so both log patterns appear in roughly
  // equal proportion, giving the masking processor a mix to work through.
  const iteration = __ITER % 2;

  if (iteration === 0) {
    doGetCustomer(BASE_URL);
  } else {
    doPostEnroll(BASE_URL);
  }

  // If a secondary target is configured, hit it on every other iteration
  if (SECONDARY_BASE_URL) {
    if (iteration === 0) {
      doPostEnroll(SECONDARY_BASE_URL);
    } else {
      doGetCustomer(SECONDARY_BASE_URL);
    }
  }

  // Brief pause between iterations — keeps throughput realistic and avoids
  // overwhelming a PoC-sized cluster
  sleep(0.5);
}
