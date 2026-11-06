with open('app/reconciliation.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'for f in db.query(ReconciliationFinding.rule_code, ReconciliationFinding.affected_record_id).all()' in line:
        new_lines.append('            for f in db.query(ReconciliationFinding.rule_code, ReconciliationFinding.affected_record_id).filter(ReconciliationFinding.review_status.in_(["PENDING", "REVIEWED"])).all()\n')
    else:
        new_lines.append(line)

with open('app/reconciliation.py', 'w') as f:
    f.writelines(new_lines)
