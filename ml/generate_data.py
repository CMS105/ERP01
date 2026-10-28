import numpy as np
import pandas as pd


def generate_dataset(seed=42, messy=False):
    """Generate repeatable synthetic LPG deliveries, payments, and planted errors."""
    rng = np.random.default_rng(seed)
    customer_count = 300
    delivery_count = 1500
    error_count = round(delivery_count * 0.03)
    overpayment_count = round(delivery_count * 0.02) if messy else 0
    split_payment_count = round(delivery_count * 0.03) if messy else 0
    late_payment_count = round(delivery_count * 0.02) if messy else 0
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
    overpayment_indices = indices[
        4 * error_count : 4 * error_count + overpayment_count
    ]
    split_payment_indices = indices[
        4 * error_count
        + overpayment_count : 4 * error_count
        + overpayment_count
        + split_payment_count
    ]
    late_payment_indices = indices[
        4 * error_count
        + overpayment_count
        + split_payment_count : 4 * error_count
        + overpayment_count
        + split_payment_count
        + late_payment_count
    ]

    deliveries.loc[duplicate_indices, "booking_id"] = deliveries.loc[
        duplicate_sources, "booking_id"
    ].to_numpy()

    missing_ids = deliveries.loc[missing_indices, "delivery_id"].tolist()
    duplicate_ids = deliveries.loc[duplicate_indices, "delivery_id"].tolist()
    underpayment_ids = deliveries.loc[underpayment_indices, "delivery_id"].tolist()
    overpayment_ids = deliveries.loc[overpayment_indices, "delivery_id"].tolist()
    missing_delivery_ids = set(missing_ids)
    underpayment_delivery_ids = set(underpayment_ids)
    overpayment_delivery_ids = set(overpayment_ids)
    split_payment_delivery_ids = set(
        deliveries.loc[split_payment_indices, "delivery_id"]
    )
    late_payment_delivery_ids = set(
        deliveries.loc[late_payment_indices, "delivery_id"]
    )

    repeat_deliveries = []
    if messy:
        repeat_count = round(customer_count * 0.03)
        repeat_customer_ids = rng.choice(
            customer_ids, size=repeat_count, replace=False
        )
        for repeat_number, customer_id in enumerate(repeat_customer_ids, start=1):
            customer_deliveries = deliveries.loc[
                deliveries["customer_id"] == customer_id
            ]
            used_days = set(
                (customer_deliveries["delivered_at"] - start).dt.days
            )
            available_days = np.array(
                [day for day in range(30) if day not in used_days]
            )
            if not len(available_days):
                raise ValueError(
                    f"No distinct delivery day available for customer {customer_id!r}."
                )
            day_offset = rng.choice(available_days)
            minute_offset = rng.integers(8 * 60, 18 * 60)
            repeat_deliveries.append(
                {
                    "delivery_id": f"D{delivery_count + repeat_number:05d}",
                    "booking_id": f"B{delivery_count + repeat_number:05d}",
                    "customer_id": customer_id,
                    "amount_due": round(
                        rng.choice([900, 950, 1000, 1050, 1100, 1150])
                        * rng.choice([1, 1, 1, 2]),
                        2,
                    ),
                    "delivered_at": (
                        start
                        + pd.to_timedelta(day_offset, unit="D")
                        + pd.to_timedelta(minute_offset, unit="m")
                    ),
                }
            )
        deliveries = pd.concat(
            [deliveries, pd.DataFrame(repeat_deliveries)], ignore_index=True
        )
        deliveries = deliveries.sort_values("delivered_at").reset_index(drop=True)

    payment_rows = []
    for row in deliveries.itertuples(index=False):
        if row.delivery_id in missing_delivery_ids:
            continue
        amount_paid = row.amount_due
        if row.delivery_id in underpayment_delivery_ids:
            amount_paid = round(row.amount_due * rng.uniform(0.7, 0.9), 2)

        if row.delivery_id in overpayment_delivery_ids:
            amount_paid = round(row.amount_due * 1.1, 2)

        paid_at = row.delivered_at
        if row.delivery_id in late_payment_delivery_ids:
            paid_at += pd.to_timedelta(rng.integers(1, 8), unit="D")

        if row.delivery_id in split_payment_delivery_ids:
            first_installment = round(amount_paid / 2, 2)
            second_installment = round(amount_paid - first_installment, 2)
            payment_rows.extend(
                [
                    (
                        f"P{len(payment_rows) + 1:05d}",
                        row.delivery_id,
                        first_installment,
                        paid_at,
                    ),
                    (
                        f"P{len(payment_rows) + 2:05d}",
                        row.delivery_id,
                        second_installment,
                        paid_at,
                    ),
                ]
            )
        else:
            payment_rows.append(
                (
                    f"P{len(payment_rows) + 1:05d}",
                    row.delivery_id,
                    amount_paid,
                    paid_at,
                )
            )

    payments = pd.DataFrame(
        payment_rows,
        columns=["payment_id", "delivery_id", "amount_paid", "paid_at"],
    )

    planted_errors = pd.DataFrame(
        [
            *(
                ("missing_payment", delivery_id)
                for delivery_id in missing_ids
            ),
            *(
                ("duplicate_booking", delivery_id)
                for delivery_id in duplicate_ids
            ),
            *(
                ("underpayment", delivery_id)
                for delivery_id in underpayment_ids
            ),
            *(
                ("amount_mismatch", delivery_id)
                for delivery_id in overpayment_ids
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
        ["missing_payment", "duplicate_booking", "underpayment", "amount_mismatch"],
        fill_value=0,
    ))
