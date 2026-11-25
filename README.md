# Outbound Pipeline | GTM Portfolio

A portfolio case study of how an outbound GTM workflow tracks prospecting, channel performance, CRM follow-up, and buyer feedback for an engineering software product.

**All accounts, activity, dates, and results are synthetic.**

## Open the demo

Open `index.html` in a browser. The demo runs from disk with no installation, server, or account.

1. Select a channel to see its funnel and CRM stage counts.
2. Turn on **Overdue follow-ups only** to see what needs action as of the demo snapshot.
3. Read the messaging tests and follow Demo Account A03 through the qualification walkthrough.

## How the tracking works

- **Cold calling** tracks accounts dialled, conversations, interest, and booked meetings.
- **LinkedIn** tracks requests, acceptances, conversations, and booked meetings.
- **Email** tracks accounts emailed, delivery, replies, and booked meetings. The denominator counts unique accounts with an attempt, including undelivered attempts. Queued accounts are outside the denominator.
- **CRM** shows current status per account. The stages run from targeted to outreached, follow-up, meeting, and proposal. Closed and lost are terminal outcomes. The stage snapshot measures where accounts sit at the reporting date.
- **Messaging tests** group attempted accounts by angle and track positive engagement, defined as interest, referral, or a booked meeting. The demo aggregates channels to illustrate the tracking. A comparison for decision-making should hold the buyer segment, channel, CTA, and observation window steady.

The dashboard counts each account once using its assigned primary channel. The dataset represents a single snapshot. A production implementation would use separate account, outreach activity, and meeting records, linked by stable IDs, to measure repeat touches, deduplicate meetings, and compare cohorts.

## Example weekly decision

Demo Account A03 progressed from LinkedIn outreach to discovery and proposal. The discovery confirmed review friction across repositories. Before advancing, confirm the sponsor, security scope, and baseline review time. Use the objections in the rest of the demo to decide which accounts to qualify out, revisit, or refer.

## Power BI companion

The [synthetic account snapshot](accounts-demo.csv) uses the same records as the web dashboard. Import it as `Accounts`. Set Due and Snapshot to Date, and StageOrder, Attempted, MeetingBooked, PositiveEngagement, and Overdue to Whole number.

Add these measures to the model.

```dax
Target Accounts = DISTINCTCOUNT(Accounts[Account])
Accounts Attempted = SUM(Accounts[Attempted])
Meetings Booked = SUM(Accounts[MeetingBooked])
Attempt to Meeting = DIVIDE([Meetings Booked], [Accounts Attempted])
Positive Engagements = SUM(Accounts[PositiveEngagement])
Overdue Follow-ups = SUM(Accounts[Overdue])
```

Use the first four measures in cards and format Attempt to Meeting as a percentage. Add Channel and Variant slicers, a stage bar chart using Target Accounts (sort Stage by StageOrder), and a tracker table with Account, Role, Stage, NextAction, and Due. Filter the tracker to Overdue = 1 for an action queue. Use a matrix by Variant with Accounts Attempted and Positive Engagements for the messaging review.

The unfiltered baseline is 16 target accounts, 14 attempts, and 3 booked meetings. Filtering to Email leaves 7 target accounts and 1 overdue follow-up. Label the report **Synthetic demo data**.
