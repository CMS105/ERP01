# India Digital Personal Data Protection (DPDP) Act 2023 - Compliance & Architecture Audit

## 1. Executive Summary
This document provides a data minimization and security architecture audit for the LPG ERP system under the India Digital Personal Data Protection (DPDP) Act, 2023. The system enforces strict purpose limitation, data minimization, role-based boundary enforcement, and sensitive credential protection across databases, API responses, Redis caching, audit logs, and AI support prompts.

---

## 2. Data Classification Matrix

| Data Element | Model / Field | Classification | Operational Purpose & Justification | Retention & Minimization Policy |
| :--- | :--- | :--- | :--- | :--- |
| **Consumer Number** | `CustomerProfile.consumer_number` | **Necessary** | Unique identifier for cylinder quotas, delivery allocation, and billing. | Retained for active connection lifecycle. |
| **Full Name** | `User.full_name` | **Necessary** | Customer identity verification during doorstep cylinder handover. | Standard operational record. |
| **Phone Number** | `User.phone` | **Sensitive** | Doorstep delivery dispatch, dispatch OTP, and SMS receipts. | Masked (`XXXXXX1234`) in public views; stored in encrypted database. |
| **Delivery Address** | `CustomerProfile.address` | **Sensitive** | Doorstep cylinder routing and safety inspections. | Accessible only to assigned delivery agent during active delivery. |
| **Raw Aadhaar Number** | N/A (Prohibited) | **Prohibited** | Never stored in plaintext or requested directly. | **Strictly prohibited**. Replaced by synthetic `aadhaar_token` / `subsidy_token`. |
| **Aadhaar Photos / Biometrics** | N/A (Prohibited) | **Prohibited** | Not required for cylinder distribution or subsidy status check. | System architecture explicitly does not store biometric artifacts. |
| **UPI PIN / CVV / Passwords** | `PaymentRecord` | **Prohibited** | Card numbers, CVVs, and UPI PINs are processed via client mPOS / gateway. | Never logged, cached, or persisted. Only gateway `transaction_reference` stored. |
| **Password Hash** | `User.hashed_password` | **Sensitive** | Account authentication. | Stored using modern salted bcrypt hashing. Never exposed via API. |
| **Audit Logs** | `AuditLog.details` | **Internal Audit** | Compliance tracking of administrative, financial, and operational mutations. | Regex redaction cleanses tokens, passwords, and 12-digit number sequences. |

---

## 3. Data Protection Principles Implemented

### 3.1 Prohibition on Direct Aadhaar Storage
- In accordance with the DPDP Act 2023 and Aadhaar regulations, raw 12-digit Aadhaar numbers and demographic biometrics are **never collected or persisted**.
- Subsidy eligibility is verified using an internal opaque reference token (`subsidy_token` / `aadhaar_token` formatted as `XXXX-XXXX-XXXX`), ensuring decoupling of national identity from ERP operational records.

### 3.2 Role-Based Access Control (RBAC) & Boundary Enforcement
- **Customer Isolation**: Backend queries enforce `Booking.customer_id == current_user.id` and `PaymentRecord.customer_id == current_user.id`. Customers cannot read or mutate any other customer's profile, booking, or financial ledger.
- **Delivery Agent Isolation**: Delivery agents can view only active tasks assigned directly to their `delivery_boy_id`. Access to completed history is limited to offline reconciliation logs.
- **Auditor Boundary**: Auditors operate under strict read-only constraints (`require_auditor`), with zero capability to mutate customer records, override cylinder inventory, or alter financial ledgers.

### 3.3 Log & Cache Sanitization
- **Redis Caching**: Redis caches only non-sensitive operational summaries (`dashboard:overview`, route recommendations, public reference data). It **never stores** customer PII, session tokens, passwords, or payment secrets.
- **Automated Audit Sanitization**: The `redact_sensitive_text()` filter strips 12-digit numeric sequences, tokens, and credentials before writing to `AuditLog`.
- **AI Prompt Minimization**: Customer support assistant prompts to Gemini strip PII, sending only the ticket category and non-identifying description.

---

## 4. Workflows for Data Subject Rights

1. **Right to Access & Correction**: Customers can review their profile and update contact details and addresses via `PUT /api/v1/customer/profile`.
2. **Right to Grievance Redressal**: An in-app support ticketing workflow (`/api/v1/customer/support/tickets`) enables automated and human-staff escalation.
3. **Audit Trail**: Administrative alterations are permanently immutably logged with timestamp, user ID, role, action, and sanitised reason.

---

## 5. Qualified Legal Notice
*This technical architecture satisfies engineering data protection and minimization best practices under the DPDP Act, 2023. Formal compliance certification requires verification by qualified legal counsel in accordance with applicable rules issued by the Data Protection Board of India.*
