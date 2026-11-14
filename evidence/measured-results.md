# Measured results (generated from actual evidence)

Generated only from on-disk k6 summaries and Kubernetes telemetry. No values are simulated.

| Scenario | Transaction rate/s | HTTP request rate/s | HTTP avg latency ms | HTTP p95 latency ms | Transaction failures % |
|---|---:|---:|---:|---:|---:|

## HPA observations

- low: No Kubernetes samples found.
- increasing: No Kubernetes samples found.
- decreasing: No Kubernetes samples found.

No HPA samples exist. Do not claim scaling occurred.

## Evidence files

- hpa-timeseries.csv: raw HPA, deployment, and CPU sampling (if recorded).
- *-summary.json: raw k6 summary for each scenario (if recorded).
- *-k6-console.log: workload console output (if recorded).
- hpa-replicas.png, hpa-cpu.png, throughput.png, response-time.png, errors.png: generated plots when supported.

## Discussion checklist

1. Did replicas increase above 1 during increasing traffic, then return toward 1 during decreasing traffic? Cite exact timestamps.
2. Compare throughput, p95 response time and error rate across three stages. Do not assume improvement.
3. Discuss database contention, login hashing CPU, EBS storage, network, HPA delays, resource limits, and node capacity as observed.
4. Clarify that HTTP request latency includes auth + write + analytics operations; HTTP requests are not identical to end-to-end transactions.
