"use strict";

const snapshot = "2025-02-21";
const stageNames = ["Targeted", "Outreached", "Follow-up", "Meeting", "Proposal", "Closed", "Lost"];

// Every row is an original fictional account, with one primary channel.
// The outcome is the highest outreach milestone or the latest feedback.
const accounts = [
  ["A01", "CTO", "Call", "Outreached", "Voicemail", "A", "Retry with the engineering lead", "2025-02-24"],
  ["A02", "VP Engineering", "Call", "Follow-up", "Interested", "B", "Send discovery times", "2025-02-20"],
  ["A03", "Head of Engineering", "LinkedIn", "Proposal", "Meeting booked", "A", "Confirm pilot scope and sponsor", "2025-02-25"],
  ["A04", "CTO", "LinkedIn", "Follow-up", "Accepted", "B", "Send a question about review workflow", "2025-02-19"],
  ["A05", "VP Engineering", "LinkedIn", "Outreached", "Request sent", "A", "Check request status", "2025-02-26"],
  ["A06", "Director of Engineering", "Email", "Follow-up", "Referral", "B", "Qualify the referred team", "2025-02-24"],
  ["A07", "Head of Engineering", "Email", "Lost", "Existing solution", "A", "Record the incumbent objection", ""],
  ["A08", "Director of Engineering", "Email", "Outreached", "Delivered", "B", "Review after the reply window", "2025-02-27"],
  ["A09", "VP Engineering", "Email", "Targeted", "Queued", "A", "Verify fit before first touch", "2025-02-25"],
  ["A10", "CTO", "Call", "Lost", "Workflow mismatch", "A", "Record the qualification gap", ""],
  ["A11", "Head of Engineering", "Call", "Meeting", "Meeting booked", "B", "Prepare discovery questions", "2025-02-24"],
  ["A12", "VP Engineering", "Email", "Follow-up", "Timing", "B", "Revisit next planning cycle", "2025-03-10"],
  ["A13", "Head of Engineering", "LinkedIn", "Follow-up", "Interested", "A", "Ask for a discovery call", "2025-02-21"],
  ["A14", "Director of Engineering", "Email", "Closed", "Meeting booked", "B", "Hand off to onboarding", ""],
  ["A15", "CTO", "Call", "Targeted", "Queued", "A", "Verify role and call window", "2025-02-26"],
  ["A16", "VP Engineering", "Email", "Outreached", "Undelivered", "A", "Verify delivery details", "2025-02-20"]
].map(([id, role, channel, stage, outcome, variant, next, due]) =>
  ({ id, role, channel, stage, outcome, variant, next, due })
);

const eligible = rows => rows.filter(row => row.outcome !== "Queued");
const engaged = ["Interested", "Referral", "Meeting booked"];
const callReached = [...engaged, "Workflow mismatch"];
const emailReplies = [...engaged, "Existing solution", "Timing"];
const booked = ["Meeting booked"];
const channels = {
  Call: ["Cold calling", [
    ["Accounts dialled", null], ["Conversations", callReached],
    ["Interested or booked", engaged], ["Meetings booked", booked]
  ]],
  LinkedIn: ["LinkedIn outreach", [
    ["Requests sent", null], ["Accepted", ["Accepted", ...engaged]],
    ["Conversations", engaged], ["Meetings booked", booked]
  ]],
  Email: ["Email outbound", [
    ["Accounts emailed", null], ["Delivered", ["Delivered", ...emailReplies]],
    ["Replies", emailReplies], ["Meetings booked", booked]
  ]]
};

function count(rows, outcomes) {
  return outcomes ? rows.filter(row => outcomes.includes(row.outcome)).length : rows.length;
}

function describeRatio(numerator, denominator) {
  if (!denominator) return "—";
  return `${numerator} / ${denominator} · ${Math.round(numerator / denominator * 100)}%`;
}

function overdue(row) {
  return Boolean(row.due && row.due < snapshot);
}

function render() {
  const channel = document.querySelector('input[name="channel"]:checked').value;
  const selected = channel === "All" ? Object.keys(channels) : [channel];
  const rows = accounts.filter(row => selected.includes(row.channel));
  const contacted = eligible(rows);
  const meetings = count(contacted, booked);
  document.querySelector("#metrics").innerHTML = [
    ["Target accounts", rows.length],
    ["Accounts attempted", contacted.length],
    ["Meetings booked", meetings],
    ["Attempt to meeting", describeRatio(meetings, contacted.length)]
  ].map(([label, value]) => `<div class="metric">${label}<strong>${value}</strong></div>`).join("");

  document.querySelector("#funnels").innerHTML = selected.map(key => {
    const [title, steps] = channels[key];
    const cohort = contacted.filter(row => row.channel === key);
    const bars = steps.map(([label, outcomes]) => {
      const value = count(cohort, outcomes);
      const width = cohort.length ? 100 * value / cohort.length : 0;
      return `<div class="bar-row"><div class="bar-label"><span>${label}</span><strong>${value}</strong></div>
        <div class="track" aria-hidden="true"><span style="width:${width}%"></span></div></div>`;
    }).join("");
    return `<article class="panel"><h3>${title}</h3>${bars}</article>`;
  }).join("");

  document.querySelector("#stages").innerHTML = stageNames.map(stage =>
    `<span>${stage} <strong>${rows.filter(row => row.stage === stage).length}</strong></span>`
  ).join("");

  const visible = document.querySelector("#overdue").checked ? rows.filter(overdue) : rows;
  document.querySelector("#tracker-count").textContent =
    `${visible.length} of ${rows.length} accounts · Demo snapshot ${snapshot}`;
  document.querySelector("#account-rows").innerHTML = visible.map(row =>
    `<tr><th scope="row">Demo Account ${row.id}</th><td>${row.role}</td><td>${row.channel}</td>
      <td>${row.stage}</td><td>${row.next}</td>
      <td${overdue(row) ? ' class="late"' : ""}>${row.due || "—"}${overdue(row) ? " · Overdue" : ""}</td></tr>`
  ).join("");
}

const variants = [
  ["A", "Review workload", "See whether AI-assisted changes are increasing the time senior engineers spend in review."],
  ["B", "Cross-repository context", "See whether missing context across repositories is making changes harder to assess."]
];

function renderReview() {
  document.querySelector("#variants").innerHTML = variants.map(([id, title, hypothesis]) => {
    const attempted = eligible(accounts).filter(row => row.variant === id);
    const positive = count(attempted, engaged);
    return `<article class="panel"><h3>${id} · ${title}</h3><p>${hypothesis}</p>
      <p><strong>${positive} of ${attempted.length}</strong> attempted accounts engaged positively.</p>
      <p>CTA for both variants is a short discovery call.</p></article>`;
  }).join("");

  const actions = [
    ["Timing", "Revisit at the next planning cycle."],
    ["Existing solution", "Ask what the current tooling leaves unresolved."],
    ["Workflow mismatch", "Check for multi-repository review before adding similar accounts."],
    ["Referral", "Qualify the suggested team before following up."]
  ];
  document.querySelector("#feedback").innerHTML = actions.map(([outcome, action]) =>
    `<li><strong>${outcome} (${count(accounts, [outcome])})</strong> · ${action}</li>`
  ).join("");
}

document.querySelector("#channels-filter").addEventListener("change", render);
document.querySelector("#overdue").addEventListener("change", render);
render();
renderReview();
