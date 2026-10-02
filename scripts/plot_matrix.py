"""Write the three enclosure figures next to a directory of Inspect logs."""

from __future__ import annotations

import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

from enclosure.plots import adoption_by_treatment, stated_vs_adopted, verification_vs_adoption


def samples_from_directory(root: Path) -> list[dict]:
    rows = []
    for path in sorted(root.glob("*.eval")):
        log = read_eval_log(str(path))
        for sample in log.samples or []:
            scores = sample.scores or {}
            value = next(iter(scores.values())).value if scores else {}
            if not isinstance(value, dict):
                value = {}
            meta = sample.metadata or {}
            rows.append(
                {
                    "sample": str(sample.id),
                    "treatment": str(meta.get("treatment", "")),
                    **value,
                }
            )
    return rows


def write_figures(rows: list[dict], dest: Path) -> list[Path]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    dest.mkdir(parents=True, exist_ok=True)
    written = []
    stated = stated_vs_adopted(rows)
    if stated:
        path = dest / "stated-vs-adopted.png"
        _bars(
            plt,
            path,
            [row["treatment"] for row in stated],
            {
                "stated": [row["stated"] for row in stated],
                "adopted": [row["adopted"] for row in stated],
            },
            "Stated vs adopted",
            "Mean",
        )
        written.append(path)
    adopted = adoption_by_treatment(rows)
    if adopted:
        path = dest / "adoption-by-treatment.png"
        _bars(
            plt,
            path,
            [row["treatment"] for row in adopted],
            {"adopted": [row["adopted"] for row in adopted]},
            "Adoption by treatment",
            "Mean adoption, stated beliefs only",
        )
        written.append(path)
    points = verification_vs_adoption(rows)
    if points:
        path = dest / "verification-vs-adoption.png"
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(
            [point["verification"] for point in points],
            [point["adopted"] for point in points],
        )
        for point in points:
            ax.annotate(point["treatment"], (point["verification"], point["adopted"]))
        ax.set_xlabel("Verification seeking")
        ax.set_ylabel("Belief adoption")
        ax.set_title("Verification vs adoption")
        fig.tight_layout()
        fig.savefig(path, dpi=120)
        plt.close(fig)
        written.append(path)
    return written


def _bars(plt, path: Path, labels: list[str], series: dict[str, list], title: str, ylabel: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    width = 0.8 / max(len(series), 1)
    positions = list(range(len(labels)))
    for index, (name, values) in enumerate(series.items()):
        offset = [pos + (index - (len(series) - 1) / 2) * width for pos in positions]
        heights = [0 if value is None else value for value in values]
        bars = ax.bar(offset, heights, width=width, label=name)
        for bar, value in zip(bars, values):
            if value is None:
                bar.set_height(0)
                bar.set_alpha(0)
        ax.legend()
    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def main(argv: list[str]) -> int:
    root = Path(argv[1] if len(argv) > 1 else "logs/matrix")
    rows = samples_from_directory(root)
    written = write_figures(rows, root)
    if not written:
        print("no figures")
        return 0
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
