-- Migration 001: Delivery Confirmation Requests and Shared Unique Transactions
-- Database: PostgreSQL 18 (lpg_erp)
-- Preserves existing tables and records

CREATE TABLE IF NOT EXISTS delivery_confirmation_requests (
    id SERIAL PRIMARY KEY,
    request_id VARCHAR(64) UNIQUE NOT NULL,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delivery_partner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id INTEGER NOT NULL REFERENCES delivery_assignments(id) ON DELETE CASCADE,
    amount_due DOUBLE PRECISION NOT NULL,
    cylinder_serial VARCHAR(64) NULL,
    cylinder_type VARCHAR(32) NOT NULL DEFAULT '14.2kg',
    status VARCHAR(32) NOT NULL DEFAULT 'REQUESTED',
    rejection_reason TEXT NULL,
    notes TEXT NULL,
    transaction_reference VARCHAR(128) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dcr_request_id ON delivery_confirmation_requests(request_id);
CREATE INDEX IF NOT EXISTS idx_dcr_booking_id ON delivery_confirmation_requests(booking_id);
CREATE INDEX IF NOT EXISTS idx_dcr_customer_id ON delivery_confirmation_requests(customer_id);
CREATE INDEX IF NOT EXISTS idx_dcr_delivery_partner_id ON delivery_confirmation_requests(delivery_partner_id);
CREATE INDEX IF NOT EXISTS idx_dcr_assignment_id ON delivery_confirmation_requests(assignment_id);
CREATE INDEX IF NOT EXISTS idx_dcr_status ON delivery_confirmation_requests(status);
CREATE INDEX IF NOT EXISTS idx_dcr_customer_status ON delivery_confirmation_requests(customer_id, status);

CREATE TABLE IF NOT EXISTS delivery_transactions (
    id SERIAL PRIMARY KEY,
    transaction_reference VARCHAR(128) UNIQUE NOT NULL,
    confirmation_request_id INTEGER NOT NULL REFERENCES delivery_confirmation_requests(id) ON DELETE CASCADE,
    booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    customer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delivery_partner_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assignment_id INTEGER NOT NULL REFERENCES delivery_assignments(id) ON DELETE CASCADE,
    delivery_execution_id INTEGER NULL REFERENCES delivery_executions(id) ON DELETE SET NULL,
    payment_record_id INTEGER NULL REFERENCES payment_records(id) ON DELETE SET NULL,
    amount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    status VARCHAR(32) NOT NULL DEFAULT 'ACCEPTED',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dt_tx_ref ON delivery_transactions(transaction_reference);
CREATE INDEX IF NOT EXISTS idx_dt_booking_id ON delivery_transactions(booking_id);
CREATE INDEX IF NOT EXISTS idx_dt_customer_id ON delivery_transactions(customer_id);
CREATE INDEX IF NOT EXISTS idx_dt_delivery_partner_id ON delivery_transactions(delivery_partner_id);
CREATE INDEX IF NOT EXISTS idx_dt_request_id ON delivery_transactions(confirmation_request_id);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'delivery_executions' AND column_name = 'transaction_reference'
    ) THEN
        ALTER TABLE delivery_executions ADD COLUMN transaction_reference VARCHAR(128) NULL;
    END IF;
END $$;
