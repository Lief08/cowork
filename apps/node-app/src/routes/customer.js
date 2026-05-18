'use strict';

const { Router } = require('express');
const { v4: uuidv4 } = require('uuid');
const logger = require('../logger');

const router = Router();

/**
 * Generates a deterministic fake SSN from a string ID.
 * These are NOT real SSNs — they exist solely to produce realistic-looking
 * patterns for the data masking PoC.
 */
function generateFakeSsn(id) {
  let hash = 0;
  for (let i = 0; i < id.length; i++) {
    hash = Math.imul(31, hash) + id.charCodeAt(i);
    hash |= 0; // convert to 32-bit int
  }
  hash = Math.abs(hash);
  const part1 = String((hash % 799) + 100).padStart(3, '0');       // 100–899
  const part2 = String((Math.floor(hash / 799) % 89) + 10).padStart(2, '0'); // 10–98
  const part3 = String((Math.floor(hash / 71111) % 8999) + 1001).padStart(4, '0'); // 1001–9999
  return `${part1}-${part2}-${part3}`;
}

/**
 * GET /api/customer/:id
 * Simulates a customer record lookup and logs a fake SSN.
 */
router.get('/:id', (req, res) => {
  const { id } = req.params;
  const ssn = generateFakeSsn(id);

  // PoC: intentional PII in log body — the collector should mask this
  logger.info(`Retrieving customer record for id=${id}, SSN: ${ssn}`);
  logger.debug(`Customer lookup completed: customerId=${id}, socialSecurityNumber=${ssn}, status=FOUND`);

  res.json({
    customerId: id,
    status: 'FOUND',
    requestId: uuidv4(),
  });
});

/**
 * POST /api/customer/enroll
 * Simulates a new customer enrolment and logs the full record including SSN.
 * Expects JSON body: { customerId, firstName, lastName, ssn, email, phoneNumber }
 */
router.post('/enroll', (req, res) => {
  const { customerId, firstName, lastName, ssn, email, phoneNumber } = req.body;

  // PoC: intentional PII in log body — the collector should mask this
  logger.info(`Enrolling new customer: firstName=${firstName}, lastName=${lastName}, SSN: ${ssn}`);
  logger.info(`Enrollment record: customerId=${customerId}, ssn=${ssn}, email=${email}, phone=${phoneNumber}`);

  const newId = uuidv4();
  logger.info(`Customer enrolled successfully: newCustomerId=${newId}, SSN: ${ssn}`);

  res.json({
    customerId: newId,
    status: 'ENROLLED',
    message: 'Customer enrollment complete',
  });
});

module.exports = router;
