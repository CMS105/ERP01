import pandas as pd

if __package__:
    from .cylinders import check_cylinder_stock
else:
    from cylinders import check_cylinder_stock


opening_stock = pd.DataFrame(
    [("2026-10-01", 10, 2)],
    columns=["date", "full", "empty"],
)

movements = pd.DataFrame(
    [
        ("M001", "2026-10-01", "dispatched", 4),
        ("M002", "2026-10-02", "returned_empty", 2),
        ("M003", "2026-10-02", "received_full", 2),
        ("M004", "2026-10-03", "sent_empty", 1),
        ("M005", "2026-10-04", "sent_empty", 5),
    ],
    columns=["movement_id", "date", "movement_type", "quantity"],
)

actual_count = pd.DataFrame(
    [
        ("2026-10-01", 6, 2),
        ("2026-10-02", 8, 4),
        ("2026-10-03", 7, 3),
        ("2026-10-04", 8, -2),
    ],
    columns=["date", "full", "empty"],
)

print(check_cylinder_stock(opening_stock, movements, actual_count))
