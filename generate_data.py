import os
import numpy as np
import pandas as pd

rng = np.random.default_rng(42)
os.makedirs("data", exist_ok=True)

N_CUST, N_BOOK, N_STAFF = 30000, 20000, 12
PRICE, SUBSIDY_AMT = 905.0, 300.0

# ---------- customers ----------
villages = [f"Village_{i:02d}" for i in range(1, 33)]
customers = pd.DataFrame({
    "customer_id": [f"C{i:05d}" for i in range(1, N_CUST + 1)],
    "name": [f"Customer {i}" for i in range(1, N_CUST + 1)],
    "village": rng.choice(villages, N_CUST),
    "phone": [f"9{rng.integers(100000000, 999999999)}" for _ in range(N_CUST)],
    "aadhaar_token": [f"XXXX-XXXX-{rng.integers(1000, 9999)}" for _ in range(N_CUST)],
    "subsidy_eligible": rng.random(N_CUST) < 0.85,
    "active": rng.random(N_CUST) < 0.97,
})

# ---------- bookings (one month) ----------
start = pd.Timestamp("2026-09-01")
active_ids = customers.loc[customers.active, "customer_id"].to_numpy()
bookings = pd.DataFrame({
    "booking_id": [f"B{i:06d}" for i in range(1, N_BOOK + 1)],
    # replace=False: each customer books at most once, so the only
    # duplicate bookings in the data are the ones we plant below
    "customer_id": rng.choice(active_ids, N_BOOK, replace=False),
    "booking_date": start + pd.to_timedelta(rng.integers(0, 30, N_BOOK), unit="D"),
})

# ---------- deliveries (one per booking) ----------
staff = rng.integers(1, N_STAFF + 1, N_BOOK)
deliveries = pd.DataFrame({
    "delivery_id": [f"D{i:06d}" for i in range(1, N_BOOK + 1)],
    "booking_id": bookings.booking_id,
    "customer_id": bookings.customer_id,
    "staff_id": [f"S{s:02d}" for s in staff],
    "delivery_date": bookings.booking_date + pd.to_timedelta(rng.integers(0, 4, N_BOOK), unit="D"),
    "amount_due": PRICE,
    "cylinder_serial": [f"CYL{x}" for x in rng.integers(100000, 999999, N_BOOK)],
})
deliveries["run_id"] = deliveries.delivery_date.dt.strftime("%m%d") + "-" + deliveries.staff_id

# ---------- payments ----------
payments = pd.DataFrame({
    "payment_id": [f"P{i:06d}" for i in range(1, N_BOOK + 1)],
    "delivery_id": deliveries.delivery_id,
    "mode": rng.choice(["CASH", "UPI"], N_BOOK, p=[0.4, 0.6]),
    "amount": PRICE,
    "paid_date": deliveries.delivery_date,
})

# ---------- cylinder movements ----------
out_rows = pd.DataFrame({
    "delivery_id": deliveries.delivery_id,
    "cylinder_serial": deliveries.cylinder_serial,
    "direction": "OUT",
    "movement_date": deliveries.delivery_date,
})
in_rows = out_rows.copy()
in_rows["direction"] = "IN"
in_rows["cylinder_serial"] = [f"CYL{x}" for x in rng.integers(100000, 999999, N_BOOK)]
movements = pd.concat([out_rows, in_rows], ignore_index=True)

# ---------- subsidy ----------
elig = customers.set_index("customer_id").subsidy_eligible
ok = deliveries[deliveries.customer_id.map(elig)]
subsidy = pd.DataFrame({
    "subsidy_id": [f"SB{i:06d}" for i in range(1, len(ok) + 1)],
    "customer_id": ok.customer_id.to_numpy(),
    "delivery_id": ok.delivery_id.to_numpy(),
    "amount": SUBSIDY_AMT,
})

# =====================================================
# PLANT ERRORS (disjoint sets of deliveries)
# =====================================================
truth = []
perm = rng.permutation(N_BOOK)
dup_book = perm[:150]
no_pay = perm[150:350]
mismatch = perm[350:470]
no_return = perm[470:650]
dup_pay = perm[650:730]

# 1. duplicate bookings
dups = bookings.iloc[dup_book].copy()
dups["booking_id"] = [f"B{N_BOOK + i + 1:06d}" for i in range(len(dups))]
for bid in dups.booking_id:
    truth.append(("DUPLICATE_BOOKING", "bookings", bid))
bookings = pd.concat([bookings, dups], ignore_index=True)

# 2. payment amount mismatch
payments.loc[mismatch, "amount"] = rng.choice([850.0, 950.0, 800.0], len(mismatch))
for did in deliveries.delivery_id.iloc[mismatch]:
    truth.append(("AMOUNT_MISMATCH", "payments", did))

# 3. duplicate payments
dp = payments.iloc[dup_pay].copy()
dp["payment_id"] = [f"P{N_BOOK + i + 1:06d}" for i in range(len(dp))]
for pid in dp.payment_id:
    truth.append(("DUPLICATE_PAYMENT", "payments", pid))

# 4. delivery without payment
no_pay_ids = set(deliveries.delivery_id.iloc[no_pay])
payments = payments[~payments.delivery_id.isin(no_pay_ids)]
payments = pd.concat([payments, dp], ignore_index=True)
for did in no_pay_ids:
    truth.append(("DELIVERY_NO_PAYMENT", "deliveries", did))

# 5. empty cylinder never returned
no_ret_ids = set(deliveries.delivery_id.iloc[no_return])
movements = movements[~((movements.direction == "IN") & movements.delivery_id.isin(no_ret_ids))]
for did in no_ret_ids:
    truth.append(("MISSING_EMPTY_RETURN", "cylinder_movements", did))

# 6. subsidy paid to ineligible customer
bad = deliveries[~deliveries.customer_id.map(elig)].sample(100, random_state=1)
bad_sub = pd.DataFrame({
    "subsidy_id": [f"SB9{i:05d}" for i in range(len(bad))],
    "customer_id": bad.customer_id.to_numpy(),
    "delivery_id": bad.delivery_id.to_numpy(),
    "amount": SUBSIDY_AMT,
})
subsidy = pd.concat([subsidy, bad_sub], ignore_index=True)
for sid in bad_sub.subsidy_id:
    truth.append(("SUBSIDY_INELIGIBLE", "subsidy", sid))

# ---------- save ----------
customers.to_csv("data/customers.csv", index=False)
bookings.to_csv("data/bookings.csv", index=False)
deliveries.to_csv("data/deliveries.csv", index=False)
payments.to_csv("data/payments.csv", index=False)
movements.to_csv("data/cylinder_movements.csv", index=False)
subsidy.to_csv("data/subsidy.csv", index=False)
pd.DataFrame(truth, columns=["error_type", "table", "record_id"]).to_csv(
    "data/ground_truth.csv", index=False)

print("Done. Planted errors:", len(truth))
