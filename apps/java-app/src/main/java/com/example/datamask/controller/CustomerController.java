package com.example.datamask.controller;

import com.example.datamask.model.CustomerRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.UUID;

/**
 * REST controller that deliberately logs PII (fake SSNs, emails, phone numbers)
 * to demonstrate OTel Collector data masking via the OTTL transform processor.
 *
 * DO NOT use this pattern in production applications.
 */
@Slf4j
@RestController
@RequestMapping("/api/customer")
public class CustomerController {

    /**
     * Simulate a customer record lookup.
     * Logs a fake SSN so the OTel Collector can redact it before forwarding.
     */
    @GetMapping("/{id}")
    public ResponseEntity<Map<String, Object>> getCustomer(@PathVariable String id) {
        String ssn = generateFakeSsn(id);
        // PoC: intentional PII in log body — the collector should mask this
        log.info("Retrieving customer record for id={}, SSN: {}", id, ssn);
        log.debug("Customer lookup completed: customerId={}, socialSecurityNumber={}, status=FOUND", id, ssn);

        return ResponseEntity.ok(Map.of(
                "customerId", id,
                "status", "FOUND",
                "requestId", UUID.randomUUID().toString()
        ));
    }

    /**
     * Simulate a new customer enrolment.
     * Logs the full enrolment record including SSN, email, and phone number.
     */
    @PostMapping("/enroll")
    public ResponseEntity<Map<String, Object>> enrollCustomer(@RequestBody CustomerRequest request) {
        // PoC: intentional PII in log body — the collector should mask this
        log.info("Enrolling new customer: firstName={}, lastName={}, SSN: {}",
                request.getFirstName(), request.getLastName(), request.getSsn());
        log.info("Enrollment record: customerId={}, ssn={}, email={}, phone={}",
                request.getCustomerId(), request.getSsn(), request.getEmail(), request.getPhoneNumber());

        String newId = UUID.randomUUID().toString();
        log.info("Customer enrolled successfully: newCustomerId={}, SSN: {}", newId, request.getSsn());

        return ResponseEntity.ok(Map.of(
                "customerId", newId,
                "status", "ENROLLED",
                "message", "Customer enrollment complete"
        ));
    }

    /**
     * Generates a deterministic fake SSN from a string ID.
     * These are NOT real SSNs — they exist solely to produce realistic-looking
     * patterns for the data masking PoC.
     */
    private String generateFakeSsn(String id) {
        int hash = Math.abs(id.hashCode());
        int part1 = (hash % 799) + 100;              // 100–899  (avoids 000, 666, 900-999)
        int part2 = (hash / 799 % 89)  + 10;         // 10–98    (avoids 00)
        int part3 = (hash / 71111 % 8999) + 1001;    // 1001–9999 (avoids 0000)
        return String.format("%03d-%02d-%04d", part1, part2, part3);
    }
}
