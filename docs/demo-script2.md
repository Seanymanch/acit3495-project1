# Demonstration script (roughly 7–10 minutes, plus the full load-test recording)

## Demo preparation

- Use `README.md` to create EKS, deploy, and run the complete 17-minute test **before** the instructor demo. Save `evidence/` charts, raw k6 outputs, and screenshots. Scaling is not instantaneous, so use recorded evidence if the demo time is short. Your instructor may request to watch a live scale-out.
- Keep two PowerShell terminals running `kubectl -n acit3495 port-forward svc/enter-data 5000:5000` and `kubectl -n acit3495 port-forward svc/show-results 3000:3000`.
- Have a third PowerShell terminal at project root, with `kubectl`, `aws`, `eksctl`, `python`, `k6` available.

## Talking points and commands

1. **Architecture (40 seconds):** show `docs/architecture.png`, explaining EKS, four services, MySQL, MongoDB, private networking, EBS persistence, HPA on auth.
2. **Actual cloud cluster (40 seconds):** `kubectl get nodes -o wide`; `kubectl -n acit3495 get deployments,statefulsets,svc,pvc,pods`.
3. **Working app (60 seconds):** open `http://localhost:5000`, log in as `student` using the privately generated demo password, insert a value, open `http://localhost:3000`, log in, show count/min/max/avg.
4. **Configuration / HPA (50 seconds):** `kubectl -n acit3495 describe hpa auth-hpa`; `kubectl -n acit3495 get hpa auth-hpa`; `kubectl top pods -n acit3495 -l app=auth`.
5. **Live load (as time allows):** open a new PowerShell terminal, set `$env:DEMO_PASSWORD = Get-Content .\secrets\demo_password.txt -Raw`, set `$env:SCENARIO = 'increasing'`, then run `k6 run k6/temperature-workload.js`. In the other terminal: `kubectl -n acit3495 get hpa auth-hpa -w`; show `kubectl -n acit3495 get pods -l app=auth -w`. (This duplicates load; do not run it concurrently with `run_experiments.py` unless intentional.)
6. **Measured 3 scenarios (60 seconds):** present `evidence/hpa-replicas.png`, `hpa-cpu.png`, `throughput.png`, `response-time.png`, `errors.png` and `performance-summary.csv`, alongside console logs and screenshots. State your ACTUAL observed replica min and max, and whether scaling out/in happened.
7. **Analysis (60 seconds):** explain whether scaling increased throughput, what changed in response times and CPU, and observed bottlenecks. Avoid claiming a result without measurements.
8. **Cleanup:** show awareness of cloud billing. After grading: `eksctl delete cluster -f cloud/eksctl-cluster.yaml` (this permanently destroys the project cluster and its data).

## Screenshot checklist

1. AWS EKS cluster name and healthy managed worker nodes.
2. `kubectl -n acit3495 get pods,deploy,statefulset,pvc,svc` with Running and Bound indicators.
3. Both web interfaces and successful temperature calculation.
4. `kubectl -n acit3495 describe hpa auth-hpa` with metrics and actual scaling event(s).
5. `kubectl top pods -n acit3495 -l app=auth` during peak.
6. `kubectl -n acit3495 get deploy auth -w` with replicas increasing and decreasing (or timestamped CSV plot).
7. k6 results for low, increasing, decreasing phases, and generated diagrams.

Do not invent screenshots, outcomes, or measured values. Capture them from your real run.
