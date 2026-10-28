import pandas as pd


if __package__:
    from .discrepancy import find_discrepancies
else:
    from discrepancy import find_discrepancies


def find_discrepancies_team_schema(bookings, deliveries, payments):
    """Adapt team-schema data and add duplicate-booking flags."""
    adapted_deliveries = deliveries.copy()
    adapted_payments = payments.copy()
    adapted_deliveries = adapted_deliveries.rename(
        columns={"delivery_date": "delivered_at"}
    )
    adapted_payments = adapted_payments.rename(
        columns={"amount": "amount_paid"}
    )

    discrepancy_flags = find_discrepancies(adapted_deliveries, adapted_payments)

    duplicate_booking_flags = []
    for _, group in bookings.groupby(
        ["customer_id", "booking_date"], sort=False, dropna=False
    ):
        first_booking_id = group.iloc[0]["booking_id"]
        for booking_id in group.iloc[1:]["booking_id"]:
            if booking_id != first_booking_id:
                duplicate_booking_flags.append(
                    {
                        "flag_type": "duplicate_booking",
                        "record_id": booking_id,
                        "evidence": (
                            f"Booking {booking_id!r} shares a customer and date "
                            f"with first booking {first_booking_id!r}."
                        ),
                    }
                )

    booking_flags = pd.DataFrame(
        duplicate_booking_flags,
        columns=["flag_type", "record_id", "evidence"],
    )
    return pd.concat(
        [discrepancy_flags, booking_flags], ignore_index=True
    )
