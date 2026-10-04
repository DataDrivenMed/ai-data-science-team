"""Academic Medicine Executive Dashboard.

Run:
    streamlit run apps/academic-medicine-executive-dashboard/app.py
"""

from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from ai_data_science_team.decision_science.domains.academic_medicine import (
    AccreditationEvidencePackage,
    AcademicMedicineCQIEngine,
    ActionStatus,
    CQIMetricSpec,
    DatasetRegistry,
    LeadershipActionRegistry,
    demo_datasets,
    demo_metric_specs,
)

st.set_page_config(
    page_title="Academic Medicine Executive Dashboard",
    page_icon="◼",
    layout="wide",
    initial_sidebar_state="expanded",
)

STATUS_COLORS = {
    "ON_TARGET": "#0F766E",
    "MONITOR": "#64748B",
    "WARNING": "#B45309",
    "CRITICAL": "#B42318",
    "NO_DATA": "#94A3B8",
}
DOMAIN_COLORS = {
    "Admissions": "#0F4C5C",
    "UME": "#1D4ED8",
    "GME": "#6D28D9",
    "Research": "#047857",
    "Workforce": "#B45309",
}

st.markdown(
    """
    <style>
    .stApp { background: #f6f7f9; }
    [data-testid="stSidebar"] { background: #0f172a; }
    [data-testid="stSidebar"] * { color: #f8fafc; }
    .block-container { max-width: 1500px; padding-top: 1.5rem; padding-bottom: 3rem; }
    h1, h2, h3 { letter-spacing: -0.025em; color: #14213d; }
    h1 { font-size: 2.05rem !important; font-weight: 700 !important; }
    h2 { font-size: 1.35rem !important; font-weight: 650 !important; }
    .eyebrow {
      text-transform: uppercase; letter-spacing: .12em; font-size: .72rem;
      color: #64748b; font-weight: 700; margin-bottom: .3rem;
    }
    .subhead { color: #64748b; font-size: .96rem; margin-top: -.25rem; margin-bottom: 1.2rem; }
    .executive-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
      padding: 1rem 1.05rem; min-height: 118px; box-shadow: 0 1px 2px rgba(15,23,42,.03);
    }
    .metric-label { color: #64748b; font-size: .75rem; text-transform: uppercase; letter-spacing: .08em; font-weight: 700; }
    .metric-value { color: #14213d; font-size: 1.75rem; font-weight: 720; line-height: 1.1; margin-top: .38rem; }
    .metric-note { color: #64748b; font-size: .78rem; margin-top: .45rem; }
    .section-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
      padding: 1.1rem 1.15rem; margin-bottom: 1rem;
    }
    .status-chip {
      display: inline-block; padding: .16rem .48rem; border-radius: 999px;
      font-size: .67rem; font-weight: 750; letter-spacing: .05em;
    }
    .status-warning { background: #fffbeb; color: #b45309; }
    .status-critical { background: #fef2f2; color: #b42318; }
    [data-testid="stTabs"] button { font-size: .86rem; font-weight: 650; }
    div[data-testid="stDataFrame"] { border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_value(value, unit):
    if value is None or pd.isna(value):
        return "No data"
    if unit == "proportion":
        return f"{float(value) * 100:.1f}%"
    if unit == "currency":
        return "$" + (f"{float(value):,.1f}" if abs(float(value)) < 1000 else f"{float(value) / 1_000_000:.1f}M")
    if unit == "count":
        return f"{float(value):,.0f}"
    return f"{float(value):,.2f}"


def load_uploaded(file):
    suffix = file.name.lower().rsplit(".", 1)[-1]
    if suffix == "csv":
        return pd.read_csv(file)
    if suffix in {"xlsx", "xls"}:
        return pd.read_excel(file)
    raise ValueError("Supported files: CSV, XLSX, XLS")


def metric_card(label, value, note):
    st.markdown(
        f"""
        <div class="executive-card">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def current_specs():
    raw = st.session_state.get("metric_specs")
    if not raw:
        raw = [spec.to_dict() for spec in demo_metric_specs()]
        st.session_state["metric_specs"] = raw
    return [CQIMetricSpec(**item) for item in raw]


def build_registry(mode):
    registry = DatasetRegistry()
    defaults = demo_datasets()
    if mode == "Demonstration":
        for name, data in defaults.items():
            registry.register(name, data, source=f"Demonstration {name} dataset", version="demo-1")
        return registry

    uploaded = st.session_state.get("uploaded_domain_data", {})
    for name in ["admissions", "ume", "gme", "research", "workforce"]:
        data = uploaded.get(name)
        if isinstance(data, pd.DataFrame):
            registry.register(name, data, source=f"Uploaded {name} dataset", version="session")
        else:
            registry.register(name, defaults[name], source=f"Demonstration fallback: {name}", version="demo-1")
    return registry


with st.sidebar:
    st.markdown("### Executive Analytics")
    institution = st.text_input("Institution", "Academic Health Sciences Center")
    reporting_label = st.text_input("Reporting period", "FY / AY 2026")
    mode = st.radio("Data mode", ["Demonstration", "Institutional upload"], index=0)
    st.divider()
    st.markdown("**View controls**")
    selected_domains = st.multiselect(
        "Domains",
        ["Admissions", "UME", "GME", "Research", "Workforce"],
        default=["Admissions", "UME", "GME", "Research", "Workforce"],
    )
    st.caption("Thresholds and definitions are controlled in Data & Configuration.")
    st.divider()
    st.caption("Decision-grade academic medicine analytics")

registry = build_registry(mode)
engine = AcademicMedicineCQIEngine(registry=registry)
specs = current_specs()

action_payload = st.session_state.get("leadership_action_registry")
action_registry = (
    LeadershipActionRegistry.from_dict(action_payload)
    if action_payload
    else LeadershipActionRegistry()
)

snapshot_rows = []
metric_errors = []
for spec in specs:
    try:
        snapshot_rows.append(engine.compute(spec).to_dict())
    except Exception as exc:
        metric_errors.append({"metric": spec.name, "error": str(exc)})
snapshot = pd.DataFrame(snapshot_rows)

trends_rows = []
for spec in specs:
    if not spec.period_column:
        continue
    try:
        dataset = registry.get(spec.dataset).data
        if spec.period_column not in dataset.columns:
            continue
        periods = dataset[spec.period_column].dropna().astype(str).drop_duplicates().sort_values()
        for period in periods:
            trends_rows.append(engine.compute(spec, period=period).to_dict())
    except Exception as exc:
        metric_errors.append({"metric": f"{spec.name} trend", "error": str(exc)})
trends = pd.DataFrame(trends_rows)

view_snapshot = snapshot.loc[snapshot["domain"].isin(selected_domains)].copy() if not snapshot.empty and selected_domains else snapshot.copy()
view_trends = trends.loc[trends["domain"].isin(selected_domains)].copy() if not trends.empty and selected_domains else trends.copy()

st.markdown('<div class="eyebrow">Academic medicine decision intelligence</div>', unsafe_allow_html=True)
st.title(f"{institution} | Executive Dashboard")
st.markdown(
    f'<div class="subhead">{reporting_label} · CQI status, longitudinal performance, evidence lineage, and leadership action</div>',
    unsafe_allow_html=True,
)

tabs = st.tabs([
    "Executive Summary",
    "CQI Radar",
    "Domain Performance",
    "Trends",
    "Evidence",
    "Leadership Actions",
    "Accreditation Evidence",
    "Data & Configuration",
])

with tabs[0]:
    total = len(view_snapshot)
    critical = int((view_snapshot["status"] == "CRITICAL").sum()) if total else 0
    warning = int((view_snapshot["status"] == "WARNING").sum()) if total else 0
    on_target = int((view_snapshot["status"] == "ON_TARGET").sum()) if total else 0
    attention = critical + warning

    cols = st.columns(5)
    with cols[0]:
        metric_card("Metrics monitored", f"{total}", "Across selected domains")
    with cols[1]:
        metric_card("On target", f"{on_target}", "Meeting configured target")
    with cols[2]:
        metric_card("Needs attention", f"{attention}", "Warning + critical")
    with cols[3]:
        metric_card("Critical", f"{critical}", "Immediate executive review")
    with cols[4]:
        rate = (attention / total) if total else 0
        metric_card("Attention rate", f"{rate * 100:.0f}%", "Share outside normal range")

    left, right = st.columns([1.25, 1])
    with left:
        st.subheader("Portfolio status")
        scorecard = engine.domain_scorecard(view_snapshot)
        if not scorecard.empty:
            plot = scorecard.melt(
                id_vars=["domain"],
                value_vars=["on_target", "monitor", "warning", "critical"],
                var_name="status",
                value_name="metrics",
            )
            fig = px.bar(
                plot,
                x="domain",
                y="metrics",
                color="status",
                barmode="stack",
                color_discrete_map={
                    "on_target": STATUS_COLORS["ON_TARGET"],
                    "monitor": STATUS_COLORS["MONITOR"],
                    "warning": STATUS_COLORS["WARNING"],
                    "critical": STATUS_COLORS["CRITICAL"],
                },
            )
            fig.update_layout(
                height=330, margin=dict(l=0, r=0, t=10, b=0),
                legend_title_text="", xaxis_title="", yaxis_title="Metrics",
                paper_bgcolor="white", plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Executive exceptions")
        exceptions = engine.exceptions(view_snapshot)
        if exceptions.empty:
            st.success("No warning or critical metrics in the selected portfolio.")
        else:
            for _, row in exceptions.head(6).iterrows():
                css = "status-critical" if row["status"] == "CRITICAL" else "status-warning"
                st.markdown(
                    f"""
                    <div class="section-card">
                      <span class="status-chip {css}">{row['status']}</span>
                      <div style="font-weight:700; margin-top:.45rem;">{row['name']}</div>
                      <div style="font-size:1.2rem; color:#14213d; margin-top:.1rem;">{format_value(row['value'], row['unit'])}</div>
                      <div class="metric-note">{row['domain']} · Owner: {row['owner']}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.subheader("Dean / leadership brief")
    brief = engine.executive_brief(
        view_snapshot,
        view_trends,
        institution_name=institution,
        as_of=datetime.now().date().isoformat(),
    )
    with st.container(border=True):
        st.markdown(brief)
    st.download_button(
        "Download leadership brief (.md)",
        data=brief.encode("utf-8"),
        file_name="academic_medicine_executive_brief.md",
        mime="text/markdown",
    )

with tabs[1]:
    st.subheader("CQI Radar")
    st.caption("Exception-first monitoring against thresholds defined in the metric registry.")
    domain_options = sorted(view_snapshot["domain"].dropna().unique()) if not view_snapshot.empty else []
    domain_filter = st.multiselect("Filter domains", domain_options, default=domain_options, key="cqi_domains")
    cqi = view_snapshot.loc[view_snapshot["domain"].isin(domain_filter)].copy() if domain_filter else view_snapshot.copy()
    if not cqi.empty:
        display = cqi[[
            "status", "domain", "name", "value", "unit", "target",
            "warning_threshold", "critical_threshold", "owner", "standard_or_element"
        ]].copy()
        display["value_display"] = [
            format_value(v, u) for v, u in zip(display["value"], display["unit"], strict=False)
        ]
        display = display.drop(columns=["value", "unit"]).rename(columns={"value_display": "value"})
        st.dataframe(display, use_container_width=True, hide_index=True)
    if metric_errors:
        with st.expander("Metric computation notices"):
            st.dataframe(pd.DataFrame(metric_errors), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Domain Performance")
    domains = sorted(view_snapshot["domain"].unique()) if not view_snapshot.empty else []
    domain = st.selectbox("Domain", domains) if domains else None
    if domain:
        subset = view_snapshot.loc[view_snapshot["domain"] == domain].copy()
        domain_trends = view_trends.loc[view_trends["domain"] == domain].copy() if not view_trends.empty else pd.DataFrame()
        cards = st.columns(min(4, max(1, len(subset))))
        for idx, (_, row) in enumerate(subset.head(4).iterrows()):
            with cards[idx]:
                metric_card(row["name"], format_value(row["value"], row["unit"]), row["status"])
        if not domain_trends.empty:
            fig = px.line(domain_trends, x="period", y="value", color="name", markers=True)
            fig.update_layout(
                height=380, margin=dict(l=0, r=0, t=30, b=0),
                xaxis_title="Period", yaxis_title="Metric value",
                legend_title_text="", paper_bgcolor="white", plot_bgcolor="white",
            )
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            subset[["status", "name", "value", "unit", "owner", "source", "standard_or_element"]],
            use_container_width=True, hide_index=True,
        )

with tabs[3]:
    st.subheader("Longitudinal Trends")
    if view_trends.empty:
        st.info("No period-based metrics are configured.")
    else:
        metric_names = sorted(view_trends["name"].unique())
        selected_metrics = st.multiselect(
            "Metrics", metric_names, default=metric_names[: min(4, len(metric_names))]
        )
        plot_data = view_trends.loc[view_trends["name"].isin(selected_metrics)].copy()
        fig = go.Figure()
        for name, subset in plot_data.groupby("name"):
            fig.add_trace(go.Scatter(
                x=subset["period"], y=subset["value"],
                mode="lines+markers", name=name,
                line=dict(width=2.5), marker=dict(size=7),
            ))
        if len(selected_metrics) == 1 and not plot_data.empty:
            target = plot_data.iloc[-1].get("target")
            if pd.notna(target):
                fig.add_hline(y=float(target), line_dash="dot", annotation_text="Target")
        fig.update_layout(
            height=480, margin=dict(l=0, r=0, t=20, b=0),
            legend_title_text="", xaxis_title="Period", yaxis_title="Metric value",
            paper_bgcolor="white", plot_bgcolor="white", hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(
            plot_data[["period", "domain", "name", "value", "status"]],
            use_container_width=True, hide_index=True,
        )

with tabs[4]:
    st.subheader("Evidence Lineage")
    st.caption("Every computed metric is tied to its registered source dataset and SHA-256 fingerprint.")
    st.markdown("#### Registered datasets")
    st.dataframe(registry.inventory(), use_container_width=True, hide_index=True)
    st.markdown("#### Metric evidence")
    evidence = pd.DataFrame([
        {
            "record_id": record.record_id,
            "kind": record.kind,
            "claim": record.claim,
            "source": record.source,
            "transformation": record.transformation,
            "dataset_fingerprint": record.dataset_fingerprint,
            "validation_status": record.validation_status,
            "created_at": record.created_at,
        }
        for record in engine.ledger.records
    ])
    if not evidence.empty:
        st.dataframe(evidence, use_container_width=True, hide_index=True)
        st.download_button(
            "Download evidence ledger (.json)",
            data=engine.ledger.to_json(indent=2).encode("utf-8"),
            file_name="academic_medicine_evidence_ledger.json",
            mime="application/json",
        )


with tabs[5]:
    st.subheader("Leadership Actions")
    st.caption(
        "Close the CQI loop by assigning corrective actions, recording executive decisions, "
        "and verifying outcomes against the same monitored metric."
    )

    exceptions = engine.exceptions(view_snapshot)
    action_summary = action_registry.summary()
    cols = st.columns(5)
    with cols[0]:
        metric_card("Open actions", str(action_summary["OPEN"]), "Awaiting execution")
    with cols[1]:
        metric_card("In progress", str(action_summary["IN_PROGRESS"]), "Active corrective work")
    with cols[2]:
        metric_card("Blocked", str(action_summary["BLOCKED"]), "Requires escalation")
    with cols[3]:
        metric_card("Verified", str(action_summary["VERIFIED"]), "Outcome confirmed")
    with cols[4]:
        metric_card("Decisions logged", str(action_summary["DECISIONS"]), "Leadership record")

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown("#### Action register")
        if st.button("Create actions from current exceptions", type="primary"):
            created = action_registry.create_from_exceptions(exceptions)
            st.session_state["leadership_action_registry"] = action_registry.to_dict()
            if created:
                st.success(f"Created {len(created)} action(s) from current warning/critical metrics.")
            else:
                st.info("No new exception actions were needed.")
            st.rerun()

        action_frame = action_registry.actions_frame()
        if action_frame.empty:
            st.info("No leadership actions have been created.")
        else:
            show_cols = [
                "action_id", "metric_name", "domain", "trigger_status", "owner",
                "status", "action", "success_criterion", "due_date", "review_date",
            ]
            st.dataframe(
                action_frame[show_cols],
                use_container_width=True,
                hide_index=True,
            )

    with right:
        st.markdown("#### Update action")
        actions = list(action_registry.actions)
        if actions:
            action_map = {
                f"{item.metric_name} · {item.action_id}": item
                for item in actions
            }
            selected_label = st.selectbox(
                "Action",
                list(action_map),
                key="leadership_action_select",
            )
            selected_action = action_map[selected_label]
            owner = st.text_input(
                "Owner",
                value=selected_action.owner,
                key="action_owner",
            )
            sponsor = st.text_input(
                "Executive sponsor",
                value=selected_action.executive_sponsor or "",
                key="action_sponsor",
            )
            action_text = st.text_area(
                "Corrective action",
                value=selected_action.action,
                key="action_text",
            )
            criterion = st.text_area(
                "Success criterion",
                value=selected_action.success_criterion,
                key="action_criterion",
            )
            status = st.selectbox(
                "Status",
                [item.value for item in ActionStatus],
                index=[item.value for item in ActionStatus].index(selected_action.status.value),
                key="action_status",
            )
            due_date = st.text_input(
                "Due date",
                value=selected_action.due_date or "",
                placeholder="YYYY-MM-DD",
                key="action_due",
            )
            review_date = st.text_input(
                "Review date",
                value=selected_action.review_date or "",
                placeholder="YYYY-MM-DD",
                key="action_review_date",
            )
            if st.button("Save action update"):
                action_registry.update_action(
                    selected_action.action_id,
                    status=status,
                    owner=owner,
                    action=action_text,
                    success_criterion=criterion,
                    due_date=due_date or None,
                    review_date=review_date or None,
                    executive_sponsor=sponsor or None,
                )
                st.session_state["leadership_action_registry"] = action_registry.to_dict()
                st.success("Action updated.")
                st.rerun()

    st.divider()
    decision_col, review_col = st.columns(2)

    with decision_col:
        st.markdown("#### Record leadership decision")
        action_items = list(action_registry.actions)
        if action_items:
            decision_action = st.selectbox(
                "Linked action",
                action_items,
                format_func=lambda item: f"{item.metric_name} · {item.action_id}",
                key="decision_action",
            )
            decision = st.text_area(
                "Decision",
                placeholder="Example: approve targeted remediation intervention for the next cohort.",
                key="decision_text",
            )
            rationale = st.text_area(
                "Rationale",
                placeholder="Record why this option was selected and what evidence was considered.",
                key="decision_rationale",
            )
            decision_maker = st.text_input(
                "Decision maker",
                placeholder="Dean / committee / executive owner",
                key="decision_maker",
            )
            options = st.text_area(
                "Options considered",
                placeholder="One option per line",
                key="decision_options",
            )
            if st.button("Record decision", key="record_decision"):
                if decision and rationale and decision_maker:
                    action_registry.record_decision(
                        metric_id=decision_action.metric_id,
                        action_id=decision_action.action_id,
                        decision=decision,
                        rationale=rationale,
                        decision_maker=decision_maker,
                        options_considered=[
                            line.strip()
                            for line in options.splitlines()
                            if line.strip()
                        ],
                        evidence_record_ids=decision_action.evidence_record_ids,
                    )
                    st.session_state["leadership_action_registry"] = action_registry.to_dict()
                    st.success("Leadership decision recorded.")
                    st.rerun()
                else:
                    st.warning("Decision, rationale, and decision maker are required.")
        else:
            st.info("Create an action before recording a decision.")

    with review_col:
        st.markdown("#### Remeasure and verify")
        action_items = list(action_registry.actions)
        if action_items:
            review_action = st.selectbox(
                "Action to review",
                action_items,
                format_func=lambda item: f"{item.metric_name} · {item.action_id}",
                key="review_action",
            )
            current_rows = view_snapshot.loc[
                view_snapshot["metric_id"] == review_action.metric_id
            ]
            if not current_rows.empty:
                current = current_rows.iloc[-1]
                st.write(
                    f"Current metric: **{format_value(current['value'], current['unit'])}** "
                    f"({current['status']})"
                )
                reviewer = st.text_input(
                    "Reviewer",
                    placeholder="CQI lead / committee chair",
                    key="outcome_reviewer",
                )
                notes = st.text_area(
                    "Outcome review notes",
                    placeholder="Document whether the corrective action changed the outcome and what happens next.",
                    key="outcome_notes",
                )
                if st.button("Verify outcome", key="verify_outcome"):
                    if reviewer:
                        evidence_ids = (
                            [str(current["evidence_record_id"])]
                            if pd.notna(current.get("evidence_record_id"))
                            else []
                        )
                        review = action_registry.review_outcome(
                            action_id=review_action.action_id,
                            measured_value=(
                                None
                                if pd.isna(current["value"])
                                else float(current["value"])
                            ),
                            metric_status=str(current["status"]),
                            reviewer=reviewer,
                            notes=notes,
                            evidence_record_ids=evidence_ids,
                        )
                        st.session_state["leadership_action_registry"] = action_registry.to_dict()
                        if review.success_met:
                            st.success("Success criterion verified. Action moved to VERIFIED.")
                        else:
                            st.warning("Outcome not yet verified. Action remains open for continued CQI.")
                        st.rerun()
                    else:
                        st.warning("Reviewer is required.")
            else:
                st.warning("The linked metric is not in the current filtered dashboard view.")

    st.markdown("#### Decision log")
    decisions = action_registry.decisions_frame()
    if decisions.empty:
        st.caption("No leadership decisions recorded.")
    else:
        st.dataframe(decisions, use_container_width=True, hide_index=True)

    st.markdown("#### Outcome verification log")
    reviews = action_registry.reviews_frame()
    if reviews.empty:
        st.caption("No post-action outcome reviews recorded.")
    else:
        st.dataframe(reviews, use_container_width=True, hide_index=True)

    st.download_button(
        "Download action / decision registry (.json)",
        data=action_registry.to_json(indent=2).encode("utf-8"),
        file_name="academic_medicine_cqi_action_registry.json",
        mime="application/json",
    )


with tabs[6]:
    st.subheader("Accreditation Evidence")
    st.caption(
        "Generate an audit-ready packet linking metric definition, longitudinal performance, "
        "source lineage, leadership actions, decisions, and outcome verification."
    )

    if view_snapshot.empty:
        st.info("No metrics are available.")
    else:
        metric_options = {
            f"{row['name']} · {row['domain']}": str(row["metric_id"])
            for _, row in view_snapshot.iterrows()
        }
        selected_metric_label = st.selectbox(
            "Metric",
            list(metric_options),
            key="evidence_metric",
        )
        selected_metric_id = metric_options[selected_metric_label]
        packet = AccreditationEvidencePackage.build(
            metric_id=selected_metric_id,
            snapshot=view_snapshot,
            trends=view_trends,
            ledger=engine.ledger,
            actions=action_registry,
        )
        metric = packet["metric"]

        cols = st.columns(4)
        with cols[0]:
            metric_card("Current status", str(metric["status"]), str(metric["domain"]))
        with cols[1]:
            metric_card(
                "Current value",
                format_value(metric["value"], metric["unit"]),
                "Latest computed result",
            )
        with cols[2]:
            metric_card(
                "Target",
                format_value(metric.get("target"), metric["unit"]),
                "Configured CQI target",
            )
        with cols[3]:
            metric_card(
                "Evidence records",
                str(len(packet["evidence_lineage"])),
                "Linked provenance records",
            )

        packet_md = AccreditationEvidencePackage.to_markdown(packet)
        with st.container(border=True):
            st.markdown(packet_md)

        download_left, download_right = st.columns(2)
        with download_left:
            st.download_button(
                "Download evidence packet (.md)",
                data=packet_md.encode("utf-8"),
                file_name=f"{selected_metric_id}_accreditation_evidence.md",
                mime="text/markdown",
            )
        with download_right:
            packet_json = AccreditationEvidencePackage.to_json(packet, indent=2)
            st.download_button(
                "Download evidence packet (.json)",
                data=packet_json.encode("utf-8"),
                file_name=f"{selected_metric_id}_accreditation_evidence.json",
                mime="application/json",
            )

with tabs[7]:
    st.subheader("Data & Configuration")
    st.caption("Intended for the analytics/CQI team rather than executive viewers.")
    st.markdown("#### Institutional datasets")
    uploaded_store = st.session_state.setdefault("uploaded_domain_data", {})
    cols = st.columns(2)
    for idx, name in enumerate(["admissions", "ume", "gme", "research", "workforce"]):
        with cols[idx % 2]:
            upload = st.file_uploader(
                f"{name.title()} dataset",
                type=["csv", "xlsx", "xls"],
                key=f"upload_{name}",
            )
            if upload is not None:
                try:
                    uploaded_store[name] = load_uploaded(upload)
                    st.success(f"Loaded {name}: {len(uploaded_store[name]):,} rows")
                except Exception as exc:
                    st.error(str(exc))

    st.markdown("#### CQI metric registry")
    config_df = pd.DataFrame([spec.to_dict() for spec in specs])
    editable_cols = [
        "metric_id", "name", "domain", "dataset", "calculator", "owner",
        "direction", "target", "warning_threshold", "critical_threshold",
        "period_column", "unit", "standard_or_element", "cadence",
    ]
    edited = st.data_editor(
        config_df[editable_cols],
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="metric_registry_editor",
    )
    if st.button("Apply metric registry", type="primary"):
        current = {spec.metric_id: spec for spec in specs}
        updated = []
        for _, row in edited.iterrows():
            metric_id = str(row["metric_id"])
            base = current.get(metric_id)
            payload = row.to_dict()
            payload["source"] = base.source if base else str(row["dataset"])
            payload["calculator_params"] = base.calculator_params if base else {}
            for key, value in list(payload.items()):
                if pd.isna(value):
                    payload[key] = None
            updated.append(CQIMetricSpec(**payload).to_dict())
        st.session_state["metric_specs"] = updated
        st.success("Metric registry updated for this session.")
        st.rerun()

    with st.expander("Metric registry JSON"):
        registry_json = json.dumps(st.session_state["metric_specs"], indent=2, default=str)
        st.code(registry_json, language="json")
        st.download_button(
            "Download metric registry",
            data=registry_json.encode("utf-8"),
            file_name="academic_medicine_metric_registry.json",
            mime="application/json",
        )

    if mode == "Institutional upload":
        st.info(
            "Uploaded datasets replace the corresponding demonstration dataset for this session. "
            "Metric calculators require the schema fields documented in docs/ACADEMIC_MEDICINE.md."
        )
