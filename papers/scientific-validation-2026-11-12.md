# Enclosure: consolidation and AI adjudication

This development version adds reproducible annotation identities and safeguards
around the experimental extensions. It is an instrument and descriptive pilot,
not a confirmatory study. Model subjects' statements are observable declarations;
no metric directly establishes their internal beliefs.

## Annotation policy and findings

The user delegated annotation to the assistant. All **84 texts** were inspected
for their stance toward the target claim: **28 affirm, 54 deny, 2 are absent**.
Authorship is explicitly `ai` (Codex). **Zero annotations are human-validated.**
Each annotation joins to campaign, source-log SHA-256, model, sample, epoch and
channel. Verbatim quotes are checked against the extracted text. The two absent
outputs belong to the false-control sample that hit its time limit: `belief_stated`
and `report_filed` are both zero, and the trace's only shell command lists files.
Neither output is counted as a denial. The historical 58 classifications agree
with the original machine annotations; that agreement is not a human gold standard.

The main VM pilot has one sample per cell for Flash and Pro on grid T0/T2/T4/T5.
Both models' declared conclusions and memos deny the false claim at T0, affirm at
T2, and deny in the finals after T4/T5 restoration. The extension smoke covers
independent-source prose, an explicit correction, observable true/false controls,
and hierarchy with a simulated console. These are individual observations, not
model rankings or causal estimates. Both models use the same provider.

The true control has an affirmative conclusion; the false control has no
conclusion. Accordingly **d-prime and criterion remain unestimated**. Uncertainty,
absence and elicited answers must remain separate before any binary decision rule
is applied. No action/belief gap is inferred from the subject's later final memo.

Versioned annotations: `labels/ai-adjudication-2026-11-12.json`. Descriptive counts,
coverage, limits and the stored numeric diagnostic confusion table are in
`annotated-results-2026-11-12.json`. Full source texts and raw traces remain local;
new campaign data are not represented as a publicly released trace dataset.

## Implementation contracts

- Runner captures immutable image IDs from the actual running containers before
  subject generation. Tag-time image IDs remain preliminary provenance only.
- New logs store complete final text snapshots, shared by analysis and review.
  Historical extraction accepts confirmed canonical writes, uses explicit final
  absence flags, and marks opaque or unconfirmed extraction unresolved.
- Review identity includes model/log/epoch; legacy YAML conversion refuses keys
  that would collapse different records. Reviewed AI labels cannot pass the
  `--require-human` guard. Extraction, stance and review status are separate fields.
- Domain exposure and successful delivery of the specific forum claim are separate
  diagnostics. A homepage fetch, 404 or unknown document version cannot establish
  claim exposure. Delivery itself does not establish cognitive attention.
- In-phase counters are serialized; completed operations and completed notice
  deliveries survive later delivery failures. Failures propagate.
- The numeric phrase scorer remains diagnostic. Version `phrase-v2` ignores
  blockquotes/code examples and normalizes digit-bearing alert acronyms; it is not
  certified as a semantic classifier by agreement on this annotated corpus.

## Shared budget

Both budget-run scripts default to **dry run** and share the repository's durable
`logs/budget/shared.json`. Its opening conservative commitment is **1.27642592 USD**
from the previous campaigns, including their 0.50 USD contingency reserve. The
cumulative ceiling is **5 USD**; remaining availability is **3.72357408 USD**.
No new paid model calls are required or made during this consolidation.

Reservations precede calls and use a peak-price bound for the sample cost limit
plus one maximum-context response overshoot. These runners disable out-of-budget
belief probes, automatic retries and concurrent samples. Cached inputs remain in
the usage accounting. Unknown/cancelled usage keeps its reservation; a repeated
campaign cannot reset the opening commitment. Overruns are recorded and block
further scheduling. Execution requires a same-day verified price profile; the
current source is the official DeepSeek pricing page linked by the runner.
Manual Inspect commands and legacy provider scripts are outside this budget-managed
entrypoint; they are not invoked by the consolidation workflow.

```bash
# Both commands plan without contacting model APIs:
uv run python scripts/run_budget_pilot.py
uv run python scripts/run_extension_smoke.py
# Explicit --execute is required for a separately intended paid run.
```

## Local review and analysis

```bash
uv run python scripts/review_bundle.py logs/pilot-v2 logs/review/new-bundle.json
# Add --campaign DIR for additional campaign directories (or pass a single .eval).
# ReviewRecord v2 records reviewer_type, rationale and evidence_quote explicitly.
uv run python scripts/check_review.py logs/review/scientific-review-ai.json
# This must fail for the AI record set:
uv run python scripts/check_review.py logs/review/scientific-review-ai.json --require-human
uv run python scripts/analyze_reviews.py logs/review/scientific-review-ai.json logs/review/new-results.json
```

Raw logs and candidate redacted exports remain outside Git. Original logs and
machine labels are not rewritten. A powered randomized campaign, an independent
human reference and additional strategic/pressure packs remain subsequent work.
