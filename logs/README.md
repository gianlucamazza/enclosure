# Inspect logs

Cited by the README Results. Inventory of the files in this tree. Dates, model, temperature, epochs, and sample counts are from each file's Inspect header (`eval.created`, `eval.model`, `eval.model_generate_config.temperature`, `eval.config.epochs`, `results.completed_samples`).

## `pilot-v2`

`deepseek/deepseek-flash`, temperature 0, one epoch, one sample per cell. Created 7 October 2026 (UTC). The sitting is dated 7–8 October in the README. Prompt and world from before the 9 October closing change (header `revision.commit` `2810162`).

| File | Created (UTC) | Task | Treatments | Completed samples |
|---|---|---|---|---|
| `2026-10-07T22-53-39-00-00_wire_PUqs7SXTAd9cPSYkAMNFwn.eval` | 2026-10-07T22:53:39Z | wire / `grid` | T0, T2, T4 | 3 |
| `2026-10-07T22-57-40-00-00_wire_bQKQXftmYLzJrTeKyuZQh6.eval` | 2026-10-07T22:57:40Z | wire / `suez` | T0, T2, T4 | 3 |
| `2026-10-07T23-03-06-00-00_wire_XAqQAaBod6eMTwczTnKugd.eval` | 2026-10-07T23:03:06Z | wire / `quake` | T0, T2, T4 | 3 |
| `2026-10-07T23-11-23-00-00_wire_iSGqav8p8rLwwheSyMuaVg.eval` | 2026-10-07T23:11:23Z | wire / `gnss` | T0, T2, T4 | 3 |
| `2026-10-07T23-18-39-00-00_wire_JLkfvrmboMAf98WZeyaTUc.eval` | 2026-10-07T23:18:39Z | wire / `fuel` | T0, T2, T4 | 3 |
| `2026-10-07T23-24-48-00-00_wire_jojMrWSgiKevfMSSSxKC6B.eval` | 2026-10-07T23:24:48Z | wire / `cloud` | T0, T2, T4 | 3 |
| `2026-10-07T23-31-52-00-00_wire_WjKfK2T7RgVqGDoYdEVtDh.eval` | 2026-10-07T23:31:52Z | wire / `newspeak` | T0, T2 | 2 |
| `2026-10-07T23-34-49-00-00_times_5Ehc3Gk4m6VJYfJfoXkALJ.eval` | 2026-10-07T23:34:49Z | times / `python4` | T0, T2, T4 | 3 |
| `2026-10-07T23-39-35-00-00_times_9KeUWTVWHkeU6gdFHEbKqj.eval` | 2026-10-07T23:39:35Z | times / `pep8031` | T0, T2, T4 | 3 |
| `2026-10-07T23-44-16-00-00_times_cU4DfgXTwGg24gSMUM2oLm.eval` | 2026-10-07T23:44:16Z | times / `python27` | T0, T2, T4 | 3 |

## `wave-2`

`deepseek/deepseek-flash`, temperature 1, three epochs. Created 9 October 2026 (UTC). Current prompt and world (header `revision.commit` `52ce3eb`). The wave was not judged (`judged` is 0 on every sample).

| File | Created (UTC) | Task | Treatments | Epochs | Completed samples |
|---|---|---|---|---|---|
| `2026-10-09T21-50-41-00-00_wire_DGHm34qjqXM8aJWDzfX8EF.eval` | 2026-10-09T21:50:41Z | wire / `grid` | T0, T2 | 3 | 6 |
| `2026-10-09T21-57-45-00-00_times_JxHR3PWT8phPPUJ9QQ3uaP.eval` | 2026-10-09T21:57:45Z | times / `python27` | T0, T2 | 3 | 6 |
| `2026-10-09T22-13-14-00-00_wire_B87FC55mTdKEygkLwLK23h.eval` | 2026-10-09T22:13:14Z | wire / `grid` | T1, T3 | 3 | 6 |

## Withheld runs

Two Wave 2 Gemini 3.8 Flash runs (`ce3BqPym`, `eutxWmGC`) failed at auth with no samples. Their logs are withheld because the error traces contain an OpenRouter account id and local home paths.

## Tokens

Sandbox exec events carry `Authorization: Bearer …` values for the fixture HTTP server. In `pilot-v2` the value is the default `inner-party`. In `wave-2` each sample uses an ephemeral hex token. These are not provider API keys.

An earlier `grid` sitting (`logs/run-1008/…`) is cited in `papers/experiment-log.md` and is **not** in this tree.
