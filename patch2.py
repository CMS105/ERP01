with open('app/reconciliation.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'def run_reconciliation(db: Session' in line:
        new_lines.append('from sqlalchemy import update\n')
        new_lines.append(line)
    elif 'run_entry.status = "COMPLETED"' in line:
        new_lines.append('''
        # Auto-resolve findings that are no longer detected
        active_findings = db.query(ReconciliationFinding).filter(
            ReconciliationFinding.review_status.in_(["PENDING", "REVIEWED"])
        ).all()

        detected_keys = {(d["rule_code"], d["affected_record_id"]) for d in all_detected}
        resolved_count = 0
        for finding in active_findings:
            if (finding.rule_code, finding.affected_record_id) not in detected_keys:
                finding.review_status = "RESOLVED"
                finding.review_reason = "Auto-resolved: Issue no longer detected in reconciliation run."
                finding.reviewed_at = datetime.now(timezone.utc)
                resolved_count += 1

        if resolved_count > 0:
            db.commit()
''')
        new_lines.append(line)
    elif '"by_rule": rule_counts' in line:
        new_lines.append(line)
        new_lines.append('            , "auto_resolved": resolved_count\n')
    else:
        new_lines.append(line)

with open('app/reconciliation.py', 'w') as f:
    f.writelines(new_lines)
