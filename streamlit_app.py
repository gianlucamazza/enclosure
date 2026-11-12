"""Experimenter view of Inspect logs: belief, memo, and scores."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import streamlit as st
from inspect_ai.log import read_eval_log

from enclosure.analysis import comparison_group
from enclosure.plots import (
    adoption_by_treatment,
    stated_vs_adopted,
    verification_vs_adoption,
)
from enclosure.review import identity

LOGS_DIR = Path("logs")


def constrain_log_directory(root: str, *, base: Path | None = None) -> Path:
    """Resolve a user-supplied log path and keep it inside the logs directory."""
    allowed = (base if base is not None else LOGS_DIR).resolve()
    resolved = Path(root).expanduser().resolve()
    if not resolved.is_relative_to(allowed):
        raise ValueError(f"Log directory {root!r} must stay inside {allowed}")
    return resolved


st.set_page_config(page_title="Enclosure", layout="wide")
st.title("Enclosure")
st.caption("Belief, desk memo, and scores from a finished run.")


@st.cache_data(ttl=60)
def load_rows(root: str) -> list[dict]:
    log_dir = constrain_log_directory(root)
    rows = []
    annotations_path = Path("papers/labels/ai-adjudication-2026-11-12.json")
    annotations = (
        {a["record_id"]: a for a in json.loads(annotations_path.read_text())["records"]}
        if annotations_path.exists()
        else {}
    )
    for path in sorted(log_dir.glob("*.eval")):
        log = read_eval_log(str(path))
        model = getattr(log.eval, "model", "") or ""
        source_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        for sample in log.samples or []:
            scores = sample.scores or {}
            value = next(iter(scores.values())).value if scores else {}
            if not isinstance(value, dict):
                value = {}
            meta = sample.metadata or {}
            rows.append(
                {
                    "log": path.name,
                    "annotations": {
                        channel: annotations.get(
                            identity(
                                path.parent.name,
                                source_sha,
                                str(model),
                                str(sample.id),
                                int(sample.epoch or 1),
                                channel,
                            )
                        )
                        for channel in ("belief", "memo")
                    },
                    "model": model,
                    "scenario": meta.get("scenario", str(sample.id).rsplit(".", 1)[0]),
                    "factors": {
                        key: meta.get(key)
                        for key in (
                            "scaffold",
                            "action_episode",
                            "pressure",
                            "deadline_actions",
                            "social",
                            "authority_hint",
                            "blind",
                            "prior",
                            "event_truth",
                        )
                    },
                    "decoding": log.eval.model_generate_config.model_dump(mode="json")
                    if log.eval.model_generate_config
                    else {},
                    "sample": str(sample.id),
                    "treatment": str(meta.get("treatment", "")),
                    "blind": str(meta.get("blind", "")),
                    "prior": str(meta.get("prior", "")),
                    "authority_hint": str(meta.get("authority_hint", "")),
                    "scores": value,
                    "provenance": meta.get("provenance", {}),
                    "backend": meta.get("backend", "unknown (historical)"),
                    "answer": next(iter(scores.values())).answer if scores else "",
                    "timeline": (next(iter(scores.values())).metadata or {}).get("timeline", [])
                    if scores
                    else [],
                }
            )
    return rows


available = (
    sorted(str(p) for p in Path("logs").iterdir() if p.is_dir() and any(p.glob("*.eval")))
    if Path("logs").exists()
    else []
)
selected = st.selectbox("Campaign", available) if available else "logs"
root = st.text_input("Log directory", value=selected)
st.caption(
    "Campaigns are shown separately. Historical prompts, runtimes and decoding can differ; label review may be incomplete."
)
try:
    rows = load_rows(root)
except ValueError as exc:
    st.error(str(exc))
    st.stop()
if not rows:
    st.info("No .eval logs in that directory yet.")
    st.stop()

labels = [
    f"{row['sample']} · {row['model']} · {row['prior'] or 'prior ?'} · {row['authority_hint'] or 'hint ?'}"
    for row in rows
]
picked = st.selectbox("Sample", options=range(len(rows)), format_func=lambda i: labels[i])
row = rows[picked]
scores = row["scores"]
provenance = row["provenance"]
st.caption(
    f"Runtime: {row['backend']} · Labels: {provenance.get('labels', 'unknown; not human-validated')}"
)
with st.expander("Run provenance and decoding"):
    st.json({"provenance": provenance or "unknown", "decoding": row["decoding"]})


rows = [item for item in rows if comparison_group(item) == comparison_group(row)]
st.caption(
    "Charts include only the selected scenario, model, factors, decoding and runtime provenance. Historical runs without provenance are shown one log at a time."
)
st.subheader("Annotated conclusions")
st.table(
    [
        {
            "channel": channel,
            "label": annotation.get("label") if annotation else "not reviewed",
            "authorship": annotation.get("reviewer_type") if annotation else "unknown",
        }
        for channel, annotation in row["annotations"].items()
    ]
)
st.caption(
    "AI annotations are exploratory and are not human validation. Missing labels are not denials."
)
st.subheader("Automated diagnostic scores")
metrics = (
    "belief_adoption",
    "historical_mention",
    "task_drift",
    "verification_seeking",
    "hole_notice",
    "task_completion",
    "oob_probe",
    "belief_elicited",
    "elicited_adoption",
    "belief_revisions",
    "evidence_before_adoption",
    "hole_reversion",
)
strip = st.container(horizontal=True)
for metric in metrics:
    with strip:
        raw = scores.get(metric)
        st.metric(metric.replace("_", " "), "—" if raw is None else f"{float(raw):.2f}")

st.subheader("Episode timeline")
if row["timeline"]:
    frame = pd.DataFrame(row["timeline"])
    kinds = sorted(frame["kind"].unique())
    shown = st.multiselect("Kinds", kinds, default=[k for k in kinds if k != "think"])
    frame = frame[frame["kind"].isin(shown)]
    frame["party"] = frame["party"].map({True: "party", False: "not party"}).fillna("")
    st.dataframe(frame, hide_index=True, width="stretch")
else:
    st.caption("This log predates the timeline. Re-run the episode to record one.")

st.subheader("Stated vs adopted")
stated = stated_vs_adopted(
    [{"treatment": row["treatment"], "sample": row["sample"], **row["scores"]} for row in rows]
)
if stated:
    st.bar_chart(pd.DataFrame(stated), x="treatment", y=["stated", "adopted"])
else:
    st.caption("No scored samples.")

adopted = adoption_by_treatment(
    [{"treatment": row["treatment"], "sample": row["sample"], **row["scores"]} for row in rows]
)
st.subheader("Diagnostic adoption by treatment")
if adopted:
    st.bar_chart(pd.DataFrame(adopted), x="treatment", y="adopted")
else:
    st.caption("No stated beliefs yet.")

points = verification_vs_adoption(
    [{"treatment": row["treatment"], "sample": row["sample"], **row["scores"]} for row in rows]
)
st.subheader("Diagnostic verification vs adoption")
if points:
    st.scatter_chart(pd.DataFrame(points), x="verification", y="adopted")
else:
    st.caption("No stated beliefs to plot.")

st.subheader("Answer")
st.write(row["answer"] or "No answer recorded.")
st.subheader("Scores")
st.dataframe(
    [
        {
            "metric": metric,
            "value": None if scores.get(metric) is None else float(scores[metric]),
        }
        for metric in metrics
    ],
    hide_index=True,
)
