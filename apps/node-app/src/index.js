'use strict';

const express = require('express');
const logger = require('./logger');
const customerRouter = require('./routes/customer');

const app = express();
const PORT = process.env.PORT || 8080;

app.use(express.json());

// ─── Health / Readiness probes ────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({ status: 'UP' });
});

app.get('/ready', (_req, res) => {
  res.json({ status: 'READY' });
});

// ─── Application routes ───────────────────────────────────────────────────────
app.use('/api/customer', customerRouter);

// ─── Start ────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  logger.info(`node-datamask-app listening on port ${PORT}`);
});

module.exports = app;
