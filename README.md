# LPG ERP Backend Architecture

Backend architecture for LPG Enterprise Resource Planning supporting four distinct user roles, backend-enforced role-based access control (RBAC), and offline-tolerant operations.

## Architecture & Clients

- **Customer (Android App)**: Bookings, profile, deliveries tracking, and payment history.
- **Delivery Boy (Android App)**: Assigned deliveries, outcome logging, payment collection, and offline batch sync.
- **Admin (Web Dashboard)**: User management, customer oversight, inventory control, assignments, operational overview, and audited financial corrections.
- **Auditor (Web Dashboard)**: Strictly read-only access to reconciliation reports, discrepancy evidence, financial summaries, and immutable audit logs.

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
                    | Shared Services & Models  |
                    | (Audit Logs & Corrections)|
                    +-------------+-------------+
                                  |
                    +-------------+-------------+
                    |   PostgreSQL / SQLite     |
                    +---------------------------+
```

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
│   ├── main.py
│   └── routers/
│       ├── __init__.py
│       ├── auth.py
│       ├── customer.py
│       ├── delivery_boy.py
│       ├── admin.py
│       └── auditor.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_customer.py
│   ├── test_delivery_boy.py
│   ├── test_admin.py
│   ├── test_auditor.py
│   └── test_rbac_matrix.py
├── requirements.txt
└── README.md
```

## Roles & Enforced Permissions

| Role | Client | Permitted Actions | Restrictions |
|---|---|---|---|
| **CUSTOMER** | Android App | View/update profile, book cylinders (within quota), view own deliveries and payment receipts. | Access limited strictly to own records. Cannot access staff, admin, or auditor tools. |
| **DELIVERY_BOY** | Android App | View assigned orders, submit delivery outcome (success/failure), collect cash/UPI payments, sync offline queue. | Limited to assigned deliveries only. Cannot reassign orders, edit prices, or access audit routes. |
| **ADMIN** | Web Dashboard | Manage users (activate/deactivate), view customers, cylinder inventory, assign delivery staff, apply audited financial corrections, overview dashboard. | Operational mutations create audit log entries. |
| **AUDITOR** | Web Dashboard | Read reconciliation reports, discrepancy evidence, financial summaries, financial correction history, system audit logs. | Strictly read-only (GET methods only). Any mutation (POST/PUT/DELETE) is denied with 403 Forbidden. |

## API Endpoints

### 1. Authentication (`/api/v1/auth`)
- `POST /register`: Register new customer and customer profile.
- `POST /login`: Authenticate credentials and receive JWT bearer token.
- `GET /me`: Get authenticated user profile.

### 2. Customer App (`/api/v1/customer`)
- `GET /profile`: Get customer profile and quota balance.
- `PUT /profile`: Update delivery address and contact number.
- `POST /bookings`: Create LPG cylinder booking (quota enforced).
- `GET /bookings`: List personal booking history.
- `GET /bookings/{id}`: View personal booking details.
- `GET /deliveries`: Track personal cylinder delivery status.
- `GET /payments`: View receipts and payment records.

### 3. Delivery Boy App (`/api/v1/delivery-boy`)
- `GET /deliveries/assigned`: List active delivery assignments for logged-in driver.
- `POST /deliveries/{assignment_id}/outcome`: Record delivery completion or failure.
- `POST /deliveries/{assignment_id}/collect-payment`: Collect cash or UPI payment.
- `POST /deliveries/sync-offline`: Batch synchronize offline queued delivery outcomes and payments.

### 4. Admin Dashboard (`/api/v1/admin`)
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

### 5. Auditor Dashboard (`/api/v1/auditor`)
- `GET /reconciliation-reports`: Three-way reconciliation (bookings vs deliveries vs payments).
- `GET /discrepancy-evidence`: Evidence of anomalies (unpaid deliveries, quota breaches, missing failure reasons).
- `GET /financial-summaries`: Net sales, collections by payment method, pending balances, correction variances.
- `GET /financial-corrections`: Immutable audit log of all financial corrections.
- `GET /audit-logs`: System audit trail of security and operational actions.

## Setup & Running

### 1. Environment Setup
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file or export environment variables:
```bash
DATABASE_URL=postgresql://username:password@localhost:5432/lpgerp
SECRET_KEY=your-secret-key-here
```
If `DATABASE_URL` is omitted, the application automatically uses SQLite (`sqlite:///./lpgerp.db`).

### 3. Start Development Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Interactive API documentation is accessible at `http://localhost:8000/docs`.

### 4. Run Test Suite
```bash
pytest -v
```
All 52 automated tests verify authentication, customer workflows, delivery operations, offline sync, admin functions, auditor read-only guarantees, and the complete cross-role RBAC matrix.
