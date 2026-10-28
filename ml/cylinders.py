import pandas as pd


def check_cylinder_stock(opening_stock, movements, actual_count=None):
    """Return flags for negative running balances and full-count gaps."""
    if opening_stock.empty:
        raise ValueError("opening_stock must contain an initial balance.")

    opening_rows = [
        (pd.Timestamp(row["date"]).normalize(), index, row)
        for index, row in opening_stock.iterrows()
    ]
    opening_date, _, opening = min(opening_rows, key=lambda item: (item[0], item[1]))
    full_stock = opening["full"]
    empty_stock = opening["empty"]
    flags = []

    # A negative opening balance is already below the allowed stock floor.
    for stock_type, balance in (("full", full_stock), ("empty", empty_stock)):
        if balance < 0:
            flags.append(
                {
                    "flag_type": "negative_stock",
                    "record_id": opening_date.date().isoformat(),
                    "evidence": (
                        f"Opening {stock_type} stock is {balance}, below zero."
                    ),
                }
            )

    effects = {
        "dispatched": ("full", -1),
        "returned_empty": ("empty", 1),
        "received_full": ("full", 1),
        "sent_empty": ("empty", -1),
    }
    movement_rows = [
        (pd.Timestamp(row["date"]).normalize(), position, row)
        for position, (_, row) in enumerate(movements.iterrows())
    ]
    movement_rows.sort(key=lambda item: (item[0], item[1]))

    expected_by_date = {opening_date: full_stock}
    for movement_date, _, movement in movement_rows:
        if movement_date < opening_date:
            raise ValueError("movements cannot precede the initial opening balance.")

        movement_type = movement["movement_type"]
        if movement_type not in effects:
            raise ValueError(f"Unsupported movement_type: {movement_type!r}")

        stock_type, direction = effects[movement_type]
        balance = full_stock if stock_type == "full" else empty_stock
        balance += direction * movement["quantity"]

        if stock_type == "full":
            full_stock = balance
        else:
            empty_stock = balance

        # Flag every movement that makes either running stock balance negative.
        if balance < 0:
            flags.append(
                {
                    "flag_type": "negative_stock",
                    "record_id": movement["movement_id"],
                    "evidence": (
                        f"{stock_type.capitalize()} stock is {balance} after "
                        f"{movement_type} movement."
                    ),
                }
            )

        expected_by_date[movement_date] = full_stock

    if actual_count is not None:
        dated_expected = sorted(expected_by_date.items())
        # Compare actual full counts with the expected end-of-day balance.
        for _, actual in actual_count.iterrows():
            count_date = pd.Timestamp(actual["date"]).normalize()
            if count_date < opening_date:
                raise ValueError("actual_count dates cannot precede the initial opening balance.")
            expected_full = next(
                balance for date, balance in reversed(dated_expected)
                if date <= count_date
            )
            if expected_full != actual["full"]:
                flags.append(
                    {
                        "flag_type": "unexplained_gap",
                        "record_id": count_date.date().isoformat(),
                        "evidence": (
                            f"Expected full stock is {expected_full}; "
                            f"actual full count is {actual['full']}."
                        ),
                    }
                )

    return pd.DataFrame(flags, columns=["flag_type", "record_id", "evidence"])
