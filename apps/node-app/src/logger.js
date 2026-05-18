'use strict';

const { createLogger, format, transports } = require('winston');

/**
 * Shared Winston logger instance.
 *
 * Winston log records are captured automatically by the EDOT Node.js agent
 * and forwarded as OTel log records via OTLP.  Log messages that contain PII
 * will be visible here and in the downstream exporter *before* the OTel
 * Collector applies its masking transform processor.
 */
const logger = createLogger({
  level: process.env.LOG_LEVEL || 'debug',
  format: format.combine(
    format.timestamp(),
    format.errors({ stack: true }),
    format.printf(({ timestamp, level, message, ...meta }) => {
      const metaStr = Object.keys(meta).length ? ` ${JSON.stringify(meta)}` : '';
      return `${timestamp} [${level.toUpperCase()}] ${message}${metaStr}`;
    })
  ),
  transports: [new transports.Console()],
});

module.exports = logger;
