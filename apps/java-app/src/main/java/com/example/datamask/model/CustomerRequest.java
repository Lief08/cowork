package com.example.datamask.model;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerRequest {
    private String customerId;
    private String firstName;
    private String lastName;
    /** Raw SSN value — intentionally included so it appears in log messages for masking PoC. */
    private String ssn;
    private String email;
    private String phoneNumber;
}
