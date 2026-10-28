# API Integration Checklist & Audit Matrix

## Overview
This document tracks the audit and alignment between the Android `APPFORLPG` client (`ApiService.kt` / Retrofit) and the FastAPI `HACKATHON 2026` backend routes (`/api/v1/`).

---

## Endpoint Comparison Matrix

| # | Endpoint Feature | Android Method | Original Android Route | FastAPI Backend Route | Match Status | Required Fixes |
|---|---|---|---|---|---|---|
| 1 | **User Login** | `login()` | `POST auth/login` | `POST /api/v1/auth/login` | ❌ Mismatch | Fix endpoint URL to `api/v1/auth/login`. Align request body to `email` & `password`. Parse `access_token`, `user_id`, `role`, `full_name`. |
| 2 | **Customer Profile** | `getProfile()` | *(Missing)* | `GET /api/v1/customer/profile` | ❌ Missing | Add `getProfile()` to `ApiService` to retrieve consumer number, address, and quota details. |
| 3 | **List Customer Bookings** | `getCustomerBookings()` | `GET customer/bookings` | `GET /api/v1/customer/bookings` | ❌ Mismatch | Fix path to `api/v1/customer/bookings`. Remove client-supplied `customer_id` query param (authenticated via JWT `require_customer`). Map `BookingOut` DTO. |
| 4 | **Create Cylinder Booking** | `createBooking()` | `POST customer/bookings` | `POST /api/v1/customer/bookings` | ❌ Mismatch | Fix path to `api/v1/customer/bookings`. Align request DTO fields (`cylinder_type`, `quantity`, `scheduled_date`). |
| 5 | **List Customer Deliveries** | `getCustomerDeliveries()` | `GET customer/deliveries` | `GET /api/v1/customer/deliveries` | ❌ Mismatch | Fix path to `api/v1/customer/deliveries`. Remove client-supplied `customer_id` query param. Map `DeliveryAssignmentOut` DTO. |
| 6 | **List Customer Payments** | `getCustomerPayments()` | *(Missing)* | `GET /api/v1/customer/payments` | ❌ Missing | Add `getCustomerPayments()` to `ApiService`. Map `PaymentRecordOut` DTO. |
| 7 | **List Assigned Deliveries** | `getAssignedDeliveries()` | `GET delivery-boy/assigned` | `GET /api/v1/delivery-boy/deliveries/assigned` | ❌ Mismatch | Fix path to `api/v1/delivery-boy/deliveries/assigned`. Remove client-supplied `delivery_boy_id` query param (authenticated via JWT `require_delivery_boy`). Map `DeliveryAssignmentOut` DTO. |
| 8 | **Record Delivery Outcome** | `recordDeliveryOutcome()` | `POST deliveries` | `POST /api/v1/delivery-boy/deliveries/{assignment_id}/outcome` | ❌ Mismatch | Fix path to `api/v1/delivery-boy/deliveries/{assignment_id}/outcome`. Align DTO to `outcome` ("DELIVERED_SUCCESS" / "FAILED_CUSTOMER_ABSENT"), `offline_sync_id`. |
| 9 | **Collect Delivery Payment** | `collectPayment()` | `POST payments` | `POST /api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment` | ❌ Mismatch | Fix path to `api/v1/delivery-boy/deliveries/{assignment_id}/collect-payment`. Align DTO to `amount`, `payment_method` ("CASH" / "UPI"), `transaction_reference`. |
| 10 | **Batch Offline Sync** | `syncOffline()` | `POST sync/batch` | `POST /api/v1/delivery-boy/sync-offline` | ❌ Mismatch | Fix path to `api/v1/delivery-boy/sync-offline`. Align batch DTO to `outcomes` list and `payments` list. Map `OfflineSyncBatchResponse`. |

---

## Security & Access Control Policy
- **No Client Identity Trust**: Client requests do not pass `customer_id` or `delivery_boy_id` in URL params or body to manipulate access. The authenticated identity is derived strictly from the JWT Bearer token on the server.
- **No Demo Token Usage**: `demo_token` credentials are recognized locally in Android for demo/offline sessions and are never sent as Bearer tokens to the server.
- **Database Backend**: Explicitly configured PostgreSQL database `postgresql://postgres:postgres@localhost:5432/lpg_erp` via `.env`.

---

## Duplicate Request Prevention & Offline Resilience
- `offline_sync_id` is tracked on the server to prevent duplicate execution records.
- Existing payment records per booking are updated in place upon sync, preventing duplicate payment rows.
- Failed sync items remain in the local Room `pending_sync_operations` queue for subsequent retries.
