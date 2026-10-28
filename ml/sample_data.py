import pandas as pd

if __package__:
    from .discrepancy import find_discrepancies
else:
    from discrepancy import find_discrepancies


deliveries = pd.DataFrame(
    [
        ("D001", "B001", "C001", 100.00, "2026-10-01"),
        ("D002", "B002", "C002", 75.00, "2026-10-02"),
        ("D003", "B003", "C003", 120.00, "2026-10-03"),
        ("D004", "B003", "C004", 60.00, "2026-10-04"),
        ("D005", "B005", "C005", 40.00, "2026-10-05"),
        ("D006", "B006", "C006", 80.00, "2026-10-06"),
    ],
    columns=["delivery_id", "booking_id", "customer_id", "amount_due", "delivered_at"],
)

payments = pd.DataFrame(
    [
        ("P001", "D001", 100.00),
        ("P003", "D003", 120.00),
        ("P004", "D004", 60.00),
        ("P005", "D005", 40.00),
        ("P006", "D006", 70.00),
    ],
    columns=["payment_id", "delivery_id", "amount_paid"],
)

print(find_discrepancies(deliveries, payments))