#!/usr/bin/env python3
"""
Gullah Geechee Biz — Central Accounting System
INTERNAL ONLY. Never deployed. Tracks all Stripe revenue.
One-directional: Stripe → accounting → reports.
"""

import json, os, datetime, csv
from pathlib import Path

HOME = os.path.expanduser("~")
ACCT_DIR = os.path.join(HOME, ".hermes", "accounting")
os.makedirs(ACCT_DIR, exist_ok=True)

LEDGER_PATH = os.path.join(ACCT_DIR, "ledger.jsonl")
METRICS_PATH = os.path.join(ACCT_DIR, "metrics.json")
DAILY_LOG = os.path.join(ACCT_DIR, "daily")


def init_ledger():
    """Initialize the accounting ledger if it doesn't exist."""
    if not os.path.exists(LEDGER_PATH):
        with open(LEDGER_PATH, "w") as f:
            f.write("")
    os.makedirs(DAILY_LOG, exist_ok=True)


def record_transaction(event_type, data):
    """
    Record a Stripe transaction to the ledger.
    event_type: 'subscription.created', 'invoice.paid', 'subscription.cancelled', etc.
    data: dict with relevant fields
    """
    init_ledger()
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "event": event_type,
        "data": data,
    }
    with open(LEDGER_PATH, "a") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def get_metrics():
    """Calculate current accounting metrics from the ledger."""
    init_ledger()
    
    if not os.path.exists(LEDGER_PATH):
        return {
            "total_revenue": 0.0,
            "active_members": 0,
            "members_by_tier": {},
            "monthly_recurring_revenue": 0.0,
            "annual_recurring_revenue": 0.0,
            "total_transactions": 0,
            "last_updated": datetime.datetime.now().isoformat(),
        }
    
    # Parse ledger
    subscriptions = {}  # customer_id -> {tier, status, amount}
    total_revenue = 0.0
    total_tx = 0
    
    with open(LEDGER_PATH) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                event = entry.get("event", "")
                data = entry.get("data", {})
                
                if event == "invoice.paid":
                    amount = data.get("amount", 0)
                    total_revenue += amount
                    total_tx += 1
                    
                    customer = data.get("customer", "")
                    tier = data.get("tier", "unknown")
                    status = data.get("status", "active")
                    interval = data.get("interval", "month")
                    
                    subscriptions[customer] = {
                        "tier": tier,
                        "status": status,
                        "amount": amount,
                        "interval": interval,
                        "last_payment": entry["timestamp"],
                    }
                
                elif event == "subscription.created":
                    customer = data.get("customer", "")
                    tier = data.get("tier", "unknown")
                    amount = data.get("amount", 0)
                    interval = data.get("interval", "month")
                    
                    if customer not in subscriptions:
                        subscriptions[customer] = {
                            "tier": tier,
                            "status": "active",
                            "amount": amount,
                            "interval": interval,
                            "last_payment": entry["timestamp"],
                        }
                
                elif event == "subscription.cancelled":
                    customer = data.get("customer", "")
                    if customer in subscriptions:
                        subscriptions[customer]["status"] = "cancelled"
                
                elif event == "subscription.updated":
                    customer = data.get("customer", "")
                    tier = data.get("tier", subscriptions.get(customer, {}).get("tier", "unknown"))
                    if customer in subscriptions:
                        subscriptions[customer]["tier"] = tier
            
            except json.JSONDecodeError:
                continue
    
    # Calculate metrics
    active = {k: v for k, v in subscriptions.items() if v["status"] == "active"}
    members_by_tier = {}
    mrr = 0.0
    arr = 0.0
    
    for customer, sub in active.items():
        tier = sub["tier"]
        members_by_tier[tier] = members_by_tier.get(tier, 0) + 1
        
        if sub["interval"] == "month":
            mrr += sub["amount"]
            arr += sub["amount"] * 12
        else:
            # Annual — convert to monthly equivalent
            mrr += sub["amount"] / 12
            arr += sub["amount"]
    
    metrics = {
        "total_revenue": round(total_revenue, 2),
        "active_members": len(active),
        "members_by_tier": members_by_tier,
        "monthly_recurring_revenue": round(mrr, 2),
        "annual_recurring_revenue": round(arr, 2),
        "total_transactions": total_tx,
        "last_updated": datetime.datetime.now().isoformat(),
    }
    
    # Save metrics
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
    
    return metrics


def record_webhook(payload):
    """
    Process a Stripe webhook event.
    This is called by the webhook handler bot.
    Returns the recorded entry.
    """
    event_type = payload.get("type", "unknown")
    data = payload.get("data", {}).get("object", {})
    
    if event_type == "invoice.paid":
        amount = data.get("amount_paid", 0) / 100  # cents to dollars
        customer = data.get("customer", "")
        lines = data.get("lines", {}).get("data", [])
        tier = "unknown"
        interval = "month"
        
        for line in lines:
            plan = line.get("plan", {})
            if plan:
                tier = plan.get("nickname", "unknown")
                interval = plan.get("interval", "month")
        
        entry = record_transaction(event_type, {
            "amount": amount,
            "customer": customer,
            "tier": tier,
            "interval": interval,
            "status": "active",
            "invoice_id": data.get("id", ""),
        })
        return entry
    
    elif event_type == "customer.subscription.created":
        plan = data.get("plan", {})
        tier = plan.get("nickname", "unknown")
        amount = (plan.get("amount", 0) or 0) / 100
        interval = plan.get("interval", "month")
        customer = data.get("customer", "")
        
        entry = record_transaction(event_type, {
            "customer": customer,
            "tier": tier,
            "amount": amount,
            "interval": interval,
        })
        return entry
    
    elif event_type == "customer.subscription.deleted":
        customer = data.get("customer", "")
        entry = record_transaction(event_type, {
            "customer": customer,
        })
        return entry
    
    elif event_type == "customer.subscription.updated":
        plan = data.get("plan", {})
        tier = plan.get("nickname", "unknown")
        customer = data.get("customer", "")
        entry = record_transaction(event_type, {
            "customer": customer,
            "tier": tier,
        })
        return entry
    
    # Unknown event type — still log it
    entry = record_transaction(event_type, {"raw": str(data)[:200]})
    return entry


def daily_report():
    """Generate a daily revenue report."""
    init_ledger()
    metrics = get_metrics()
    
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    report = f"""# Gullah Geechee Biz — Daily Revenue Report
Date: {today}

## Summary
- Active Members: {metrics['active_members']}
- Monthly Recurring Revenue: ${metrics['monthly_recurring_revenue']:.2f}
- Annual Recurring Revenue: ${metrics['annual_recurring_revenue']:.2f}
- Total Revenue All Time: ${metrics['total_revenue']:.2f}
- Total Transactions: {metrics['total_transactions']}

## Members by Tier
"""
    
    for tier, count in sorted(metrics['members_by_tier'].items()):
        report += f"- {tier}: {count}\n"
    
    report += f"""
## Progress to $10k/month
Target: $10,000.00/mo
Current: ${metrics['monthly_recurring_revenue']:.2f}/mo
Remaining: ${max(0, 10000 - metrics['monthly_recurring_revenue']):.2f}/mo
Progress: {min(100, (metrics['monthly_recurring_revenue'] / 10000) * 100):.1f}%
"""
    
    # Save daily report
    report_path = os.path.join(DAILY_LOG, f"{today}.md")
    with open(report_path, "w") as f:
        f.write(report)
    
    return report, metrics


def main():
    import sys
    
    init_ledger()
    
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        report, metrics = daily_report()
        print(report)
        print(json.dumps(metrics))
    elif len(sys.argv) > 1 and sys.argv[1] == "metrics":
        metrics = get_metrics()
        print(json.dumps(metrics, indent=2))
    elif len(sys.argv) > 1 and sys.argv[1] == "webhook":
        # Read webhook payload from stdin
        payload = json.loads(sys.stdin.read())
        entry = record_webhook(payload)
        print(json.dumps(entry, indent=2))
    else:
        metrics = get_metrics()
        print("=" * 60)
        print("  GULLAH GEECHEE BIZ — CENTRAL ACCOUNTING")
        print(f"  Date: {datetime.date.today().strftime('%B %d, %Y')}")
        print("=" * 60)
        print()
        print(f"  Active Members:     {metrics['active_members']}")
        print(f"  Monthly Revenue:    ${metrics['monthly_recurring_revenue']:.2f}")
        print(f"  Annual Revenue:     ${metrics['annual_recurring_revenue']:.2f}")
        print(f"  Total Revenue:      ${metrics['total_revenue']:.2f}")
        print(f"  Total Transactions: {metrics['total_transactions']}")
        print()
        print("  Members by Tier:")
        for tier, count in sorted(metrics['members_by_tier'].items()):
            print(f"    {tier}: {count}")
        print()
        print(f"  Progress to $10k/mo: {min(100, (metrics['monthly_recurring_revenue'] / 10000) * 100):.1f}%")
        print("=" * 60)


if __name__ == "__main__":
    main()
