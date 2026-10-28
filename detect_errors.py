import pandas as pd

d = "data/"
customers = pd.read_csv(d + "customers.csv")
bookings = pd.read_csv(d + "bookings.csv")
deliveries = pd.read_csv(d + "deliveries.csv")
payments = pd.read_csv(d + "payments.csv")
movements = pd.read_csv(d + "cylinder_movements.csv")
subsidy = pd.read_csv(d + "subsidy.csv")
truth = pd.read_csv(d + "ground_truth.csv")

found = []

dup = bookings[bookings.duplicated(["customer_id", "booking_date"], keep="first")]
found += [("DUPLICATE_BOOKING", x) for x in dup.booking_id]

paid = set(payments.delivery_id)
found += [("DELIVERY_NO_PAYMENT", x) for x in deliveries.delivery_id if x not in paid]

dp = payments[payments.duplicated("delivery_id", keep="first")]
found += [("DUPLICATE_PAYMENT", x) for x in dp.payment_id]

first = payments.drop_duplicates("delivery_id", keep="first")
m = first.merge(deliveries[["delivery_id", "amount_due"]], on="delivery_id")
bad = m[m.amount != m.amount_due]
found += [("AMOUNT_MISMATCH", x) for x in bad.delivery_id]

ins = set(movements[movements.direction == "IN"].delivery_id)
outs = movements[movements.direction == "OUT"].delivery_id
found += [("MISSING_EMPTY_RETURN", x) for x in outs if x not in ins]

c = customers.set_index("customer_id")
s = subsidy[~subsidy.customer_id.map(c.subsidy_eligible) | ~subsidy.customer_id.map(c.active)]
found += [("SUBSIDY_INELIGIBLE", x) for x in s.subsidy_id]

found_df = pd.DataFrame(found, columns=["error_type", "record_id"])
t = truth[["error_type", "record_id"]]

hit = t.merge(found_df, on=["error_type", "record_id"])
print("Planted:", len(t), "| Found correctly:", len(hit))
print("False alarms:", len(found_df) - len(hit))
print(t.groupby("error_type").size().to_frame("planted").join(
    hit.groupby("error_type").size().to_frame("found")))
