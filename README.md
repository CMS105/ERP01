# LPG ERP Backend & Reconciliation Engine

Enterprise Resource Planning backend architecture for LPG cylinder operations with four-role backend RBAC, offline synchronization, and an integrated PostgreSQL reconciliation engine.

## Architecture & Clients

- **Customer (Android App)**: Bookings, profile, deliveries tracking, and payment history.
- **Delivery Boy (Android App)**: Assigned deliveries, outcome logging, payment collection, and offline batch sync.
- **Admin (Web Dashboard)**: User management, customer oversight, inventory control, assignments, operational overview, audited financial corrections, and triggering reconciliation.
- **Auditor (Web Dashboard)**: Strictly read-only access to reconciliation reports, flagged records, discrepancy evidence, financial summaries, and immutable audit logs.

```
                    +---------------------------+
                    |       FastAPI Core        |
                    | JWT Auth & Backend RBAC   |
                    +-------------+-------------+
                                  |
     +-----------------+----------+----------+-----------------+
     |                 |                     |                 |
+----+----+       +----+----+           +----+----+       +----+----+
|Customer |       |Delivery |           |  Admin  |       | Auditor |
| Router  |       | Boy     |           | Router  |       | Router  |
|(Android)|       | Router  |           | (Web)   |       | (Web -  |
|         |       |(Android)|           |         |       |ReadOnly)|
+----+----+       +----+----+           +----+----+       +----+----+
     |                 |                     |                 |
     +-----------------+----------+----------+-----------------+
                                  |
                    +-------------+-------------+
                    |   Reconciliation Engine   |
                    |   6 Database Rules (SQL)  |
                    +-------------+-------------+
                                  |
                    +-------------+-------------+
                    | Shared Services & Models  |
                    | (Audit Logs & Corrections)|
                    +-------------+-------------+
                                  |
                    +-------------+-------------+
                    |   PostgreSQL / SQLite     |
                    +---------------------------+
```

## Reconciliation Rules

The engine detects discrepancies directly from PostgreSQL database models:

1. **`DUPLICATE_BOOKING`**: Flags multiple bookings made for the same customer on the same booking date (keeps first, flags subsequent duplicates).
2. **`DELIVERY_NO_PAYMENT`**: Flags completed cylinder deliveries that have no matching payment record in the ledger.
3. **`DUPLICATE_PAYMENT`**: Flags deliveries where more than one payment collection has been recorded.
4. **`AMOUNT_MISMATCH`**: Flags deliveries where the collected payment amount does not match the delivery amount due.
5. **`MISSING_EMPTY_RETURN`**: Flags deliveries where a full cylinder was dispatched OUT, but no empty cylinder was received IN.
6. **`SUBSIDY_INELIGIBLE`**: Flags subsidy credits disbursed to customers marked as ineligible or inactive.

## Directory Structure

```
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── auth.py
│   ├── services.py
│   ├── reconciliation.py
│   ├── data_loader.py
│   ├── main.py
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       ├── customer.py
│       ├── delivery_boy.py
│       ├── admin.py
│       ├── auditor.py
│       └── reconciliation.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_customer.py
│   ├── test_delivery_boy.py
│   ├── test_admin.py
│   ├── test_auditor.py
│   ├── test_rbac_matrix.py
│   └── test_reconciliation.py
├── generate_data.py
├── detect_errors.py
├── index.html
├── requirements.txt
└── README.md
```

## API Endpoints

### Authentication (`/api/v1/auth`)
- `POST /register`: Register new customer and profile.
- `POST /login`: Authenticate credentials and receive JWT bearer token.
- `GET /me`: Get authenticated user profile.

### Customer App (`/api/v1/customer`)
- `GET /profile`: Get customer profile and quota balance.
- `PUT /profile`: Update delivery address and contact number.
- `POST /bookings`: Create LPG cylinder booking (quota enforced).
- `GET /bookings`: List personal booking history.
- `GET /bookings/{id}`: View personal booking details.
- `GET /deliveries`: Track personal cylinder delivery status.
- `GET /payments`: View receipts and payment records.

### Delivery Boy App (`/api/v1/delivery-boy`)
- `GET /deliveries/assigned`: List active delivery assignments for logged-in driver.
- `POST /deliveries/{assignment_id}/outcome`: Record delivery completion or failure.
- `POST /deliveries/{assignment_id}/collect-payment`: Collect cash or UPI payment.
- `POST /deliveries/sync-offline`: Batch synchronize offline queued delivery outcomes and payments.

### Admin Dashboard (`/api/v1/admin`)
- `GET /users`: List users filtered by role.
- `POST /users`: Provision staff, auditor, or admin accounts.
- `PUT /users/{id}/status`: Activate or deactivate user access.
- `GET /customers`: List registered consumers.
- `GET /customers/{id}`: View consumer profile.
- `GET /inventory`: View cylinder inventory.
- `POST /inventory`: Add new cylinders to inventory.
- `PUT /inventory/{id}`: Update cylinder inventory status.
- `GET /bookings`: List all consumer bookings.
- `POST /bookings/{id}/assign`: Assign booking to delivery personnel and cylinder.
- `POST /financial/correct`: Apply audited financial correction on payment records.
- `GET /dashboard/overview`: Get operational summary stats.

### Auditor Dashboard (`/api/v1/auditor`)
- `GET /reconciliation-reports`: Three-way reconciliation (bookings vs deliveries vs payments).
- `GET /discrepancy-evidence`: Evidence of anomalies (unpaid deliveries, quota breaches, missing failure reasons).
- `GET /financial-summaries`: Net sales, collections by payment method, pending balances, correction variances.
- `GET /financial-corrections`: Immutable audit log of all financial corrections.
- `GET /audit-logs`: System audit trail of security and operational actions.

### Reconciliation Engine (`/api/v1/reconciliation`)
- `POST /run`: Trigger reconciliation against database records (Admin only).
- `GET /findings`: Paginated, searchable, filterable list of flagged findings (Admin & Auditor).
- `GET /runs`: View reconciliation execution history (Admin & Auditor).
- `GET /summary`: Summary statistics grouped by rule, severity, and review status (Admin & Auditor).
- `PUT /findings/{finding_id}/review`: Mark a finding as REVIEWED, RESOLVED, or DISMISSED with recorded reason and audit logging (Admin only).

## Web Dashboard (`/console`)
Access the web console at `http://localhost:8000/console`. It provides real-time integration with backend APIs for Admin and Auditor roles, including running reconciliation, filtering flagged records, and reviewing discrepancies.

## Commands

### 1. Run Backend Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Generate Synthetic Dataset
```bash
python generate_data.py
```

### 3. Run Prototype Detection Evaluation
```bash
python detect_errors.py
```

### 4. Run Automated Test Suite
```bash
pytest -v
```
All 68 tests verify the authentication system, customer isolation, delivery boy operations, admin controls, auditor restrictions, the six detection rules, idempotency, review actions, and evaluation against `ground_truth.csv`.
