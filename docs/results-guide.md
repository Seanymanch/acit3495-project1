# How to interpret the real measurements

## Collected data

- `evidence/low-summary.json`, `increasing-summary.json`, and `decreasing-summary.json`: k6 summaries with HTTP latency, HTTP request rate, errors, iteration rate and custom authenticated transaction failure rate.
- `evidence/hpa-timeseries.csv`: timestamp, scenario, HPA observed replica count, HPA desired count, ready replicas, average HPA CPU utilization as **a percent of CPU REQUEST**, and summed CPU usage in millicores if Metrics API is available.
- `evidence/performance-summary.csv`: extracted comparable numeric metrics.
- `evidence/*.png`: automatic charts. `evidence/measured-results.md`: auto-extracted values and discussion checklist.

## Answer the assignment's four discussion questions

**Q4. Did backend scale out and scale in?** Look at `hpa-replicas.png` and the min/max/final replica counts per phase. Evidence of scaling out requires actual replicas > 1 during the increasing phase. Scale-in requires a later falling count once traffic subsides. Provide actual timestamps and if relevant HPA events from `kubectl -n acit3495 describe hpa auth-hpa`.

**Q5. Did scaling improve capacity?** Compare transactions per second (not just HTTP request count) and failure rate across phases. Compare against your baseline and the range of replicas. More replicas do not automatically prove improvement: MySQL, analytics, or the single front-end replicas may bottleneck. If your increasing run hits a ceiling, report it.

**Q6. How did response time, throughput and CPU change?** Record p95 and mean latency from each phase, transaction throughput, CPU usage and average utilization. Note that `http_req_duration` is **one HTTP request latency**, and one authenticated temperature transaction causes multiple HTTP requests (login POST, redirects, submit POST, redirect). k6 reports values accurately, but the labels must be interpreted accurately.

**Q7. What limitations/bottlenecks?** Evaluate MySQL writes, Mongo snapshot update, analytics on every submission, CPU-heavy PBKDF2, front-end worker count, pod resource quotas, node capacity, and HPA metrics/stabilization. Only state which were OBSERVED (rather than speculative) when you have supporting output.

**Important controls:** use the same application code, same cluster, same `ANALYTICS_MODE=sql`, and record test duration for all scenarios. Low vs decreasing phases differ in prior HPA replica history, which is intentional. K6 load varies concurrency; this is not a randomized scientific A/B benchmark. Cluster nodes do not autoscale in the provided design.
