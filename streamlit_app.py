"""Experimenter view of Inspect logs: belief, memo, and scores."""

from pathlib import Path

import streamlit as st
from inspect_ai.log import read_eval_log

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
                    "scores": value,
                    "answer": next(iter(scores.values())).answer if scores else "",
                }
            )
    return rows


root = st.text_input("Log directory", value="logs")
rows = load_rows(root)
if not rows:
    st.info("No .eval logs in that directory yet.")
    st.stop()

labels = [f"{row['sample']} · {row['model']}" for row in rows]
picked = st.selectbox("Sample", options=range(len(rows)), format_func=lambda i: labels[i])
row = rows[picked]
scores = row["scores"]
metrics = (
    "belief_adoption",
    "task_drift",
    "verification_seeking",
    "hole_notice",
    "task_completion",
    "oob_probe",
)
strip = st.container(horizontal=True)
for metric in metrics:
    with strip:
        raw = scores.get(metric)
        st.metric(metric.replace("_", " "), "—" if raw is None else f"{float(raw):.2f}")

st.subheader("Answer")
st.write(row["answer"] or "No answer recorded.")
st.subheader("Scores")
st.dataframe(
    [{"metric": metric, "value": scores.get(metric, "")} for metric in metrics],
    hide_index=True,
)
