import numpy as np
import pandas as pd


def generate_dataset(seed=42):
    """Generate repeatable synthetic LPG deliveries, payments, and planted errors."""
    rng = np.random.default_rng(seed)
    customer_count = 300
    delivery_count = 1500
    error_count = round(delivery_count * 0.03)
    village_count = 10

    customer_ids = np.array(
        [
            f"V{village_number:02d}-C{customer_number:03d}"
            for village_number in range(1, village_count + 1)
            for customer_number in range(1, customer_count // village_count + 1)
        ]
    )
    delivery_customer_ids = np.concatenate(
        [
            customer_ids,
            rng.choice(customer_ids, size=delivery_count - customer_count),
        ]
    )
    rng.shuffle(delivery_customer_ids)

    start = pd.Timestamp("2026-01-01")
    day_offsets = rng.integers(0, 30, size=delivery_count)
    minute_offsets = rng.integers(8 * 60, 18 * 60, size=delivery_count)
    delivered_at = start + pd.to_timedelta(day_offsets, unit="D") + pd.to_timedelta(
        minute_offsets, unit="m"
    )
    delivery_order = np.argsort(delivered_at.to_numpy())

    deliveries = pd.DataFrame(
        {
            "delivery_id": [
                f"D{delivery_number:05d}"
                for delivery_number in range(1, delivery_count + 1)
            ],
            "booking_id": [
                f"B{booking_number:05d}"
                for booking_number in range(1, delivery_count + 1)
            ],
            "customer_id": delivery_customer_ids,
            "amount_due": np.round(rng.choice([900, 950, 1000, 1050, 1100, 1150], size=delivery_count)
                                    * rng.choice([1, 1, 1, 2], size=delivery_count), 2),
            "delivered_at": delivered_at,
        }
    ).iloc[delivery_order].reset_index(drop=True)

    indices = rng.permutation(delivery_count)
    missing_indices = indices[:error_count]
    duplicate_indices = indices[error_count : 2 * error_count]
    underpayment_indices = indices[2 * error_count : 3 * error_count]

    # Reuse a distinct delivery's booking ID for each planted duplicate.
    duplicate_sources = indices[3 * error_count : 4 * error_count]
    deliveries.loc[duplicate_indices, "booking_id"] = deliveries.loc[
        duplicate_sources, "booking_id"
    ].to_numpy()

    missing_delivery_ids = set(deliveries.loc[missing_indices, "delivery_id"])
    underpayment_delivery_ids = set(
        deliveries.loc[underpayment_indices, "delivery_id"]
    )
    payment_rows = []
    for row in deliveries.itertuples(index=False):
        if row.delivery_id in missing_delivery_ids:
            continue
        amount_paid = row.amount_due
        if row.delivery_id in underpayment_delivery_ids:
            amount_paid = round(row.amount_due * rng.uniform(0.7, 0.9), 2)

        payment_rows.append(
            (f"P{len(payment_rows) + 1:05d}", row.delivery_id, amount_paid)
        )

    payments = pd.DataFrame(
        payment_rows, columns=["payment_id", "delivery_id", "amount_paid"]
    )

    planted_errors = pd.DataFrame(
        [
            *(
                ("missing_payment", delivery_id)
                for delivery_id in deliveries.loc[missing_indices, "delivery_id"]
            ),
            *(
                ("duplicate_booking", delivery_id)
                for delivery_id in deliveries.loc[duplicate_indices, "delivery_id"]
            ),
            *(
                ("underpayment", delivery_id)
                for delivery_id in deliveries.loc[underpayment_indices, "delivery_id"]
            ),
        ],
        columns=["error_type", "record_id"],
    )
    return deliveries, payments, planted_errors


if __name__ == "__main__":
    deliveries, payments, planted_errors = generate_dataset()
    print(f"Deliveries: {len(deliveries)}")
    print(f"Payments: {len(payments)}")
    print("Planted errors:")
    print(planted_errors["error_type"].value_counts().reindex(
        ["missing_payment", "duplicate_booking", "underpayment"], fill_value=0
    ))
