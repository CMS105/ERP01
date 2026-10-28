import pandas as pd


def find_discrepancies(deliveries, payments):
    """Return one row per detected delivery discrepancy."""
    payment_totals = payments.groupby("delivery_id")["amount_paid"].sum()
    paid_delivery_ids = set(payments["delivery_id"])
    first_delivery_by_booking = {}
    flags = []

    for _, delivery in deliveries.iterrows():
        delivery_id = delivery["delivery_id"]
        booking_id = delivery["booking_id"]

        # A delivery with no associated payment is missing a payment.
        if delivery_id not in paid_delivery_ids:
            flags.append(
                {
                    "flag_type": "missing_payment",
                    "record_id": delivery_id,
                    "evidence": "No payment is associated with this delivery.",
                }
            )

        # Flag each repeated booking after its first delivery.
        if booking_id in first_delivery_by_booking:
            flags.append(
                {
                    "flag_type": "duplicate_delivery",
                    "record_id": delivery_id,
                    "evidence": (
                        f"Booking {booking_id!r} was already used by delivery "
                        f"{first_delivery_by_booking[booking_id]!r}."
                    ),
                }
            )
        else:
            first_delivery_by_booking[booking_id] = delivery_id

        # Compare the amount due with all payments for deliveries that were paid.
        if delivery_id in paid_delivery_ids:
            total_paid = payment_totals[delivery_id]
            if total_paid != delivery["amount_due"]:
                flags.append(
                    {
                        "flag_type": "amount_mismatch",
                        "record_id": delivery_id,
                        "evidence": (
                            f"Amount due is {float(delivery['amount_due']):.2f}; "
                            f"total paid is {float(total_paid):.2f}."
                        ),
                    }
                )

    return pd.DataFrame(flags, columns=["flag_type", "record_id", "evidence"])