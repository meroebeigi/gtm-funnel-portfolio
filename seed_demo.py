"""Recreate the original synthetic outbound and CRM export fixtures."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / "demo-exports"
RAW.mkdir(exist_ok=True)


def write(name, rows):
    with (RAW / name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


with (ROOT / "accounts-demo.csv").open(newline="", encoding="utf-8") as file:
    baseline = list(csv.DictReader(file))

crm = []
for row in baseline:
    fields = {key: row[key] for key in ("Account", "Role", "Channel", "Stage", "Variant", "NextAction", "Due", "Snapshot")}
    previous = dict(fields, Snapshot="2025-02-14")
    previous["Stage"] = {"A03": "Meeting", "A11": "Follow-up", "A14": "Proposal"}.get(row["Account"], row["Stage"])
    crm.extend((previous, fields))
write("crm.csv", crm)

for channel in ("Call", "LinkedIn", "Email"):
    events = []
    for row in baseline:
        if row["Channel"] != channel or row["Attempted"] != "1":
            continue
        account = row["Account"]
        touch_day = "2025-02-12" if account == "A04" else "2025-02-18"
        events.append(dict(Activity=f"{channel}-{account}", Account=account,
                           Time=f"{touch_day}T10:00:00", Outcome=row["Outcome"],
                           Meeting=f"M-{account}" if row["MeetingBooked"] == "1" else ""))
    if channel == "Email":
        events.append(dict(Activity="Email-A03", Account="A03", Time="2025-02-19T10:00:00",
                           Outcome="Meeting booked", Meeting="M-A03"))
        events.append(dict(Activity="Email-invalid", Account="A08", Time="invalid",
                           Outcome="Delivered", Meeting=""))
    write(f"{channel.lower()}.csv", events)
