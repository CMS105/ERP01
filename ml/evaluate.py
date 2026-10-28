if __package__:
    from .discrepancy import find_discrepancies
    from .generate_data import generate_dataset
else:
    from discrepancy import find_discrepancies
    from generate_data import generate_dataset


ERROR_TYPE_TO_FLAG = {
    "missing_payment": "missing_payment",
    "duplicate_booking": "duplicate_delivery",
    "underpayment": "amount_mismatch",
}


def _metrics(expected, detected):
    true_positives = expected & detected
    false_positives = detected - expected
    false_negatives = expected - detected
    precision = (
        len(true_positives) / len(detected) if detected else 0.0
    )
    recall = len(true_positives) / len(expected) if expected else 0.0
    return (
        len(true_positives),
        len(false_positives),
        len(false_negatives),
        precision,
        recall,
        false_positives,
        false_negatives,
    )


def _print_metrics(label, expected, detected):
    (
        true_positives,
        false_positives,
        false_negatives,
        precision,
        recall,
        false_positive_records,
        false_negative_records,
    ) = _metrics(expected, detected)
    print(
        f"{label}: true positives={true_positives}, "
        f"false positives={false_positives}, false negatives={false_negatives}, "
        f"precision={precision:.3f}, recall={recall:.3f}"
    )
    if false_positive_records:
        print(f"  Example false positives: {sorted(false_positive_records)[:3]}")
    if false_negative_records:
        print(f"  Example false negatives: {sorted(false_negative_records)[:3]}")
    return false_positive_records, false_negative_records


def main():
    deliveries, payments, planted_errors = generate_dataset()
    flags = find_discrepancies(deliveries, payments)

    expected_by_type = {}
    detected_by_type = {}
    booking_by_delivery = deliveries.set_index("delivery_id")["booking_id"]
    for error_type, flag_type in ERROR_TYPE_TO_FLAG.items():
        expected_records = planted_errors.loc[
            planted_errors["error_type"] == error_type, "record_id"
        ]
        detected_records = flags.loc[
            flags["flag_type"] == flag_type, "record_id"
        ]
        if flag_type == "duplicate_delivery":
            # Either delivery row is a valid hit because both identify the same duplicated booking.
            expected_ids = booking_by_delivery.loc[expected_records].tolist()
            detected_ids = booking_by_delivery.loc[detected_records].tolist()
        else:
            expected_ids = expected_records.tolist()
            detected_ids = detected_records.tolist()

        expected = {(flag_type, record_id) for record_id in expected_ids}
        detected = {(flag_type, record_id) for record_id in detected_ids}
        expected_by_type[flag_type] = expected
        detected_by_type[flag_type] = detected
        _print_metrics(flag_type, expected, detected)

    expected_all = set().union(*expected_by_type.values())
    detected_all = set().union(*detected_by_type.values())
    _print_metrics("overall", expected_all, detected_all)


if __name__ == "__main__":
    main()
