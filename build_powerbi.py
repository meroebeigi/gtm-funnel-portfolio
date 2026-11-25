"""Generate a portable PBIP with embedded synthetic data and native visuals."""
import json

SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item"


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def artifact(path, schema, **content):
    write(path, {"$schema": f"{SCHEMA}/{schema}/schema.json", **content})


def model_table(name, rows, measures):
    columns = []
    types = []
    for field, sample in rows[0].items():
        kind = "int64" if isinstance(sample, int) else "string"
        columns.append(dict(name=field, dataType=kind, sourceColumn=field,
                            summarizeBy="none", **({"sortByColumn": "StageOrder"} if field == "Stage" else {})))
        types.append(f'#"{field}" = {"number" if kind == "int64" else "text"}')
    # Power Query table values are embedded so moving the project needs no path edits.
    schema = ", ".join(types)
    values = ",\n".join("{" + ", ".join(
        str(value) if isinstance(value, int) else '"' + value.replace('"', '""') + '"'
        for value in row.values()) + "}" for row in rows)
    expression = f"#table(type table [{schema}], {{\n{values}\n}})"
    return dict(name=name, columns=columns,
                measures=[dict(name=label, expression=dax, formatString=fmt)
                          for label, dax, fmt in measures],
                partitions=[dict(name=name, mode="import", source=dict(type="m", expression=expression.splitlines()))])


def projection(table, field, measure=False):
    return dict(field={"Measure" if measure else "Column": {
        "Expression": {"SourceRef": {"Entity": table}}, "Property": field}},
        queryRef=f"{table}.{field}", nativeQueryRef=field, active=True)


def visual(page, name, kind, position, **roles):
    x, y, width, height = position
    artifact(page / "visuals" / name / "visual.json",
             "report/definition/visualContainer/2.0.0", name=name,
             position=dict(x=x, y=y, width=width, height=height, z=0),
             visual=dict(visualType=kind, query=dict(queryState={
                 role: dict(projections=fields) for role, fields in roles.items()
             }), drillFilterOtherVisuals=True))


def generate(root, crm, funnel):
    name = "Outbound Pipeline"
    report_name = f"{name}.Report"
    model_name = f"{name}.SemanticModel"
    report = root / report_name
    model = root / model_name
    definition = report / "definition"
    artifact(root / f"{name}.pbip", "pbip/pbipProperties/1.0.0",
             version="1.0", artifacts=[dict(report=dict(path=report_name))],
             settings=dict(enableAutoRecovery=True))
    artifact(report / "definition.pbir", "report/definitionProperties/2.0.0",
             version="4.0", datasetReference=dict(byPath=dict(path=f"../{model_name}")))
    artifact(model / "definition.pbism", "semanticModel/definitionProperties/1.0.0",
             version="1.0", settings={})
    metrics = [
        ("Attempted accounts", 'CALCULATE(DISTINCTCOUNT(Funnel[Account]), Funnel[Attempted] = 1)', "0"),
        ("Reached accounts", 'CALCULATE(DISTINCTCOUNT(Funnel[Account]), Funnel[Reached] = 1)', "0"),
        ("Responded accounts", 'CALCULATE(DISTINCTCOUNT(Funnel[Account]), Funnel[Replied] = 1)', "0"),
        ("Positive engagements", 'CALCULATE(DISTINCTCOUNT(Funnel[Account]), Funnel[PositiveEngagement] = 1)', "0"),
        ("Attributed meetings", 'SUM(Funnel[Meetings])', "0"),
        ("Attempt to meeting", 'DIVIDE([Attributed meetings], [Attempted accounts])', "0.0%"),
    ]
    crm_columns = [{**row, "Follow-up status": "Overdue" if row["Overdue"] else "Current",
                    "Qualification": ("Review friction across repositories confirmed. Confirm sponsor, "
                                      "security scope and baseline review time."
                                      if row["Account"] == "A03" else "")} for row in crm]
    crm_metrics = [("Target accounts", "DISTINCTCOUNT(CRM[Account])", "0"),
                   ("Overdue follow-ups", "SUM(CRM[Overdue])", "0")]
    write(model / "model.bim", dict(name=name, compatibilityLevel=1600,
          model=dict(culture="en-US", defaultPowerBIDataSourceVersion="powerBI_V3",
                     tables=[model_table("Funnel", funnel, metrics), model_table("CRM", crm_columns, crm_metrics)])))

    pages = ["OutreachOverview", "PipelineReview"]
    artifact(definition / "version.json", "report/definition/versionMetadata/1.0.0", version="2.0.0")
    artifact(definition / "report.json", "report/definition/report/2.0.0",
             themeCollection=dict(baseTheme=dict(name="CY24SU02", type="SharedResources",
                                                reportVersionAtImport="5.55")))
    artifact(definition / "pages" / "pages.json", "report/definition/pagesMetadata/1.0.0",
             pageOrder=pages, activePageName=pages[0])
    for page_id, title, table in zip(pages, ("Outreach funnel", "CRM and qualification"), ("Funnel", "CRM")):
        page = definition / "pages" / page_id
        artifact(page / "page.json", "report/definition/page/2.0.0", name=page_id,
                 displayName=f"{title} | Synthetic demo data", displayOption="FitToPage",
                 width=1440, height=840)
        for index, field in enumerate(("Channel", "Role", "Variant")):
            visual(page, f"Slicer{index}", "slicer", (24 + index * 465, 20, 438, 126),
                   Values=[projection(table, field)])
        if table == "Funnel":
            for index, (label, _, _) in enumerate(metrics[:3] + metrics[4:]):
                visual(page, f"Card{index}", "card", (24 + index * 278, 166, 260, 94),
                       Values=[projection(table, label, True)])
            visual(page, "ChannelFunnel", "barChart", (24, 278, 688, 500),
                   Category=[projection(table, "Channel")],
                   Y=[projection(table, label, True) for label, _, _ in metrics[:5]])
            visual(page, "MessagingVariants", "tableEx", (732, 278, 684, 500),
                   Values=[projection(table, "Variant"),
                           *(projection(table, label, True) for label in ("Attempted accounts", "Positive engagements", "Attributed meetings", "Attempt to meeting"))])
        else:
            visual(page, "Stages", "barChart", (24, 166, 890, 294),
                   Category=[projection(table, "Stage")], Y=[projection(table, "Target accounts", True)])
            visual(page, "OverdueCount", "card", (938, 166, 478, 105),
                   Values=[projection(table, "Overdue follow-ups", True)])
            visual(page, "FollowUpStatus", "slicer", (938, 287, 478, 173),
                   Values=[projection(table, "Follow-up status")])
            visual(page, "Tracker", "tableEx", (24, 482, 1392, 323),
                   Values=[projection(table, field) for field in
                           ("Account", "Stage", "Follow-up status", "NextAction", "Due", "Qualification")])
