"""Build deterministic GTM outputs and update the Power BI project data."""
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGES = ("Targeted", "Outreached", "Follow-up", "Meeting", "Proposal", "Closed", "Lost")
OUTCOMES = {
    "Call": {"Voicemail", "Interested", "Meeting booked", "Workflow mismatch"},
    "LinkedIn": {"Accepted", "Request sent", "Interested", "Meeting booked"},
    "Email": {"Referral", "Existing solution", "Delivered", "Timing", "Undelivered", "Meeting booked"},
}
POSITIVE = {"Interested", "Referral", "Meeting booked"}


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        yield from enumerate(csv.DictReader(file), start=2)


def write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build(raw, output):
    issues = []
    snapshots = {}
    events = {}

    def issue(source, line, reason):
        issues.append(dict(Source=source, Line=line, Reason=reason))

    for line, row in read_csv(raw / "crm.csv"):
        try:
            account = row["Account"]
            day = date.fromisoformat(row["Snapshot"])
            key = (day, account)
            if row["Due"]:
                date.fromisoformat(row["Due"])
            if not all(row[field] for field in ("Account", "Role", "Variant", "Stage", "Channel")):
                raise ValueError("Missing required value")
            if row["Stage"] not in STAGES or row["Channel"] not in OUTCOMES:
                raise ValueError("Unknown stage or channel")
            if key in snapshots:
                raise ValueError("Duplicate CRM account snapshot")
            snapshots[key] = row
        except (TypeError, ValueError, KeyError) as error:
            issue("crm.csv", line, str(error))

    if not snapshots:
        raise ValueError("No valid CRM snapshots")
    as_of = max(day for day, _ in snapshots)
    current = {account: row for (day, account), row in snapshots.items() if day == as_of}
    prior_days = [day for day, _ in snapshots if day < as_of]
    prior_day = max(prior_days, default=None)
    for channel, outcomes in OUTCOMES.items():
        source = f"{channel.lower()}.csv"
        for line, row in read_csv(raw / source):
            try:
                timestamp = datetime.strptime(row["Time"], "%Y-%m-%dT%H:%M:%S")
                key = (channel, row["Activity"])
                if not row["Activity"] or row["Account"] not in current:
                    raise ValueError("Missing activity ID or unknown account")
                if row["Outcome"] not in outcomes:
                    raise ValueError("Unknown outcome")
                if (row["Outcome"] == "Meeting booked") != bool(row["Meeting"]):
                    raise ValueError("Meeting ID must accompany exactly the booked outcome")
                if timestamp.date() > as_of:
                    raise ValueError("Activity falls after snapshot")
                if key in events:
                    raise ValueError("Duplicate activity ID")
                events[key] = dict(row, Channel=channel, Source=source, Line=line)
            except (TypeError, ValueError, KeyError) as error:
                issue(source, line, str(error))

    ordered = sorted(events.values(), key=lambda row: (row["Time"], row["Channel"], row["Activity"]))
    meetings = {}
    accepted = []
    for row in ordered:
        meeting = row["Meeting"]
        winner = meetings.get(meeting)
        if winner and winner["Account"] != row["Account"]:
            issue(row["Source"], row["Line"], "Meeting ID conflicts with another account")
            continue
        if winner:
            issue(row["Source"], row["Line"], "Duplicate meeting observation")
        elif meeting:
            meetings[meeting] = row
        accepted.append(row)

    crm_rows = []
    funnel_rows = []
    for account, row in sorted(current.items()):
        due = date.fromisoformat(row["Due"]) if row["Due"] else None
        previous = snapshots.get((prior_day, account))
        last_touch = max((e["Time"] for e in accepted if e["Account"] == account), default="")
        last_touch_date = date.fromisoformat(last_touch[:10]) if last_touch else None
        crm_rows.append(dict(row, StageOrder=STAGES.index(row["Stage"]) + 1,
                             PriorStage=previous["Stage"] if previous else "",
                             LastTouch=last_touch, Overdue=int(bool(due and due < as_of and row["Stage"] not in {"Closed", "Lost"})),
                             Stalled=int(bool(previous and previous["Stage"] == row["Stage"]
                                              and row["Stage"] in {"Outreached", "Follow-up", "Meeting", "Proposal"}
                                              and (not last_touch_date or as_of - last_touch_date >= timedelta(days=7))))))
        for channel in OUTCOMES:
            touches = [e for e in accepted if e["Account"] == account and e["Channel"] == channel]
            if not touches and row["Channel"] != channel:
                continue
            outcomes = {e["Outcome"] for e in touches}
            funnel_rows.append(dict(Account=account, Channel=channel, Role=row["Role"], Variant=row["Variant"],
                                    Attempted=int(bool(touches)),
                                    Reached=int(bool(outcomes - {"Voicemail", "Request sent", "Undelivered"})),
                                    Replied=int(bool(outcomes & (POSITIVE | {"Workflow mismatch", "Existing solution", "Timing"}))),
                                    PositiveEngagement=int(bool(outcomes & POSITIVE)),
                                    Meetings=sum(e["Account"] == account and e["Channel"] == channel for e in meetings.values())))

    output.mkdir(parents=True, exist_ok=True)
    write_csv(output / "crm-snapshot.csv", list(crm_rows[0]), crm_rows)
    write_csv(output / "channel-funnel.csv", list(funnel_rows[0]), funnel_rows)
    meeting_fields = ["Meeting", "Account", "Channel", "Time", "Activity"]
    write_csv(output / "meetings.csv", meeting_fields,
              ({key: row[key] for key in meeting_fields} for _, row in sorted(meetings.items())))
    write_csv(output / "validation.csv", ["Source", "Line", "Reason"], issues)
    write_csv(output / "follow-ups.csv", list(crm_rows[0]), (row for row in crm_rows if row["Overdue"]))
    brief = [f"# Weekly GTM review | {as_of}", "", "**Synthetic demo data**", "",
             f"{len(current)} target accounts. {len(meetings)} deduplicated meetings observed through the snapshot.", ""]
    sections = {
        "Stage movement": [f"{r['Account']} moved from {r['PriorStage']} to {r['Stage']}." for r in crm_rows
                           if r["PriorStage"] and r["PriorStage"] != r["Stage"]],
        "Stalled accounts": [f"{r['Account']} remains in {r['Stage']}." for r in crm_rows if r["Stalled"]],
        "Overdue follow-ups": [f"{r['Account']} · {r['Due']} · {r['NextAction']}" for r in crm_rows if r["Overdue"]],
    }
    for title, items in sections.items():
        brief.extend([f"## {title}", "", *(f"- {item}" for item in items or ["None in this snapshot."]), ""])
    (output / "weekly-review.md").write_text("\n".join(brief), encoding="utf-8", newline="\n")
    return crm_rows, funnel_rows


if __name__ == "__main__":
    from build_powerbi import generate

    crm, funnel = build(ROOT / "demo-exports", ROOT / "generated")
    generate(ROOT / "power-bi", crm, funnel)
