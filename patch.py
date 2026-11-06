with open('app/reconciliation.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if line.strip() == 'from sqlalchemy import func, or_':
        new_lines.append(line)
        new_lines.append('from app.reconciliation_sources import live_rule_delivery_no_payment, live_rule_amount_mismatch\n')
    elif line.strip() == '("SUBSIDY_INELIGIBLE", rule_subsidy_ineligible),':
        new_lines.append(line)
        new_lines.append('    ("LIVE_DELIVERY_NO_PAYMENT", live_rule_delivery_no_payment),\n')
        new_lines.append('    ("LIVE_AMOUNT_MISMATCH", live_rule_amount_mismatch),\n')
    else:
        new_lines.append(line)

with open('app/reconciliation.py', 'w') as f:
    f.writelines(new_lines)
