"""Experimenter view of Inspect logs: belief, memo, and scores."""

from pathlib import Path

import pandas as pd
import streamlit as st
from inspect_ai.log import read_eval_log

from enclosure.plots import (
    adoption_by_treatment,
    stated_vs_adopted,
    verification_vs_adoption,
)

st.set_page_config(page_title="Enclosure", layout="wide")
st.title("Enclosure")
st.caption("Belief, desk memo, and scores from a finished run.")


@st.cache_data(ttl=60)
def load_rows(root: str) -> list[dict]:
    rows = []
    for path in sorted(Path(root).glob("*.eval")):
        log = read_eval_log(str(path))
        model = getattr(log.eval, "model", "") or ""
        for sample in log.samples or []:
            scores = sample.scores or {}
            value = next(iter(scores.values())).value if scores else {}
            if not isinstance(value, dict):
                value = {}
            meta = sample.metadata or {}
            rows.append(
                {
                    "log": path.name,
                    "model": model,
                    "sample": str(sample.id),
                    "treatment": str(meta.get("treatment", "")),
                    "blind": str(meta.get("blind", "")),
                    "prior": str(meta.get("prior", "")),
                    "authority_hint": str(meta.get("authority_hint", "")),
                    "scores": value,
                    "answer": next(iter(scores.values())).answer if scores else "",
                    "timeline": (next(iter(scores.values())).metadata or {}).get("timeline", [])
                    if scores
                    else [],
                }
            )
    return rows


root = st.text_input("Log directory", value="logs/matrix")
rows = load_rows(root)
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
st.subheader("Adoption by treatment")
if adopted:
    st.bar_chart(pd.DataFrame(adopted), x="treatment", y="adopted")
else:
    st.caption("No stated beliefs yet.")

points = verification_vs_adoption(
    [{"treatment": row["treatment"], "sample": row["sample"], **row["scores"]} for row in rows]
)
st.subheader("Verification vs adoption")
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
