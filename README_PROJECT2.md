# ACIT 3495 Project 2: Cloud Deployment and Horizontal Scalability

**Chosen cloud:** AWS EKS in `us-west-2`. **Real Project 1 app:** Enter Data (Flask), Auth (FastAPI), Analytics (FastAPI), Show Results (Express), MySQL 8.4 and MongoDB 7. **Scaling target:** auth backend, 1–5 replicas, target CPU 60%. **Load tool:** k6 with low, increasing and decreasing demand.

This is a deployment-ready complete source + configuration + test + report/presentation package, built from the previously saved Project 1 source archive. It is **not a claim that AWS resources are already running** or that live scaling or measurements have occurred. To meet the rubric, you must run this against AWS EKS, capture evidence and enter the observed results in the report and slides.

## What's inside

`auth/`, `analytics/`, `enter-data/`, `show-results/`, `mysql/`, `mongo/`: complete Project 1 source; `compose.yaml` retained for local fallback. `k8s/`: namespace, ConfigMaps, EBS storage, MongoDB/MySQL StatefulSets, all four microservice Deployments/Services, 1–5 auth HPA, and optional public demo frontends. `cloud/`: EKS cluster config. `scripts/`: image build/push, secret provisioning, deployment, smoke test, three k6 runs, CPU/replica logging, charts, doc/report generator. `k6/`: actual app load scenario. `docs/`: architecture PNG/DOT, report DOCX, PPTX deck, demo script and rubric map. `evidence/`: place for actual results.

## Prerequisites (on your Windows/PowerShell computer)

- AWS account with **permission to create EKS, IAM roles, EC2, EBS and optionally LoadBalancers**, with billing enabled. AWS CLI configured to your own allowed account (`aws sts get-caller-identity`).
- Recent `eksctl`, `kubectl`, Docker Desktop, Python 3.12+, Node 22+ (optional for tests), k6. Install these from their official sources. Run `aws --version`, `eksctl version`, `kubectl version --client`, `docker --version`, `python --version`, `k6 version`.
- GHCR access: run `docker login ghcr.io` (use a GitHub token for packages with appropriate rights, or existing authenticated Docker credential helper). The four GHCR packages must be **publicly pullable**, or a configured Kubernetes imagePullSecret must be supplied to `scripts/deploy.py`. Source repo can remain private.
- **Money:** EKS control plane, 3 managed EC2 nodes, EBS disks and optional load balancers incur AWS charges until deleted. This architecture is for coursework, not the cheapest possible cloud deployment.
- The cluster uses `t3.medium` x3 and gp3 volumes; your AWS quota and AZ support must allow them. Don't create duplicate clusters.

## Step 1: Open the project and run source tests

Extract the ZIP. In **PowerShell**, open a terminal in `ACIT3495_Project2_Complete`:

```powershell
python -m pip install -r requirements-project2.txt
python -m unittest discover -s tests -v
cd show-results
npm install
npm test
cd ..
```

Your app's local `compose.yaml` is preserved. To test it locally you may run `python scripts/generate_secrets.py` then `docker compose up -d --build` before Kubernetes deployment, and `docker compose down` afterward. No passwords are prepackaged.

## Step 2: Create AWS EKS

Verify the account/region FIRST:

```powershell
aws sts get-caller-identity
aws configure get region
```

Review `cloud/eksctl-cluster.yaml` for names, size and costs. Then:

```powershell
eksctl create cluster -f cloud/eksctl-cluster.yaml
aws eks update-kubeconfig --region us-west-2 --name acit3495-p2
kubectl get nodes
kubectl top nodes
kubectl -n kube-system get deployment metrics-server
kubectl -n kube-system get deployment ebs-csi-controller
```

`eksctl` provisions required EKS and add-ons. **Do not proceed** until `kubectl top nodes` works and the EBS CSI controller is healthy. Some restricted AWS accounts require administrator approval for IAM / Pod Identity policies, especially EBS CSI. If the add-on reports permission errors, use your AWS account administrator and the official EBS CSI documentation before proceeding. You can use an **existing authorized EKS cluster instead** by configuring kubectl context and verifying the CSI driver.

## Step 3: Generate demo secrets, build and push the real application images

```powershell
python scripts/generate_secrets.py
docker login ghcr.io
python scripts/build_push.py --owner seanymanch --tag p2-v1
```

If your real GHCR namespace differs, replace `seanymanch`. Tag names must match in the next step. **Never commit `secrets/*.txt`**, Docker auth, AWS keys, or screenshots exposing them. Passwords are randomly generated locally, not included in the archive.

## Step 4: Deploy all services to EKS

```powershell
python scripts/deploy.py --owner seanymanch --tag p2-v1
kubectl -n acit3495 get pods,deploy,statefulset,svc,pvc,hpa
kubectl -n acit3495 describe hpa auth-hpa
kubectl top pods -n acit3495 -l app=auth
```

If GHCR packages are private, first create an image pull secret securely in namespace `acit3495` using your authorized registry workflow and append `--image-pull-secret NAME` to the deploy command. The standard deploy script substitutes GHCR image names and tags, applies the namespace/config, creates a Kubernetes Secret from locally generated secret files without printing it, waits for both databases and the four deployments to be ready, then applies the HPA.

If PVCs stay `Pending`: `kubectl -n acit3495 describe pvc`, `kubectl -n kube-system logs deployment/ebs-csi-controller --all-containers=true --tail=100`. Check CSI addon/permissions and available nodes/AZs. If pods report `ImagePullBackOff`: `kubectl -n acit3495 describe pod POD_NAME`, verify GHCR package visibility and image tag. If HPA shows `<unknown>`: verify Metrics Server, CPU requests, and `kubectl top pods`.

## Step 5: Open both cloud-hosted apps and verify all services

Open TWO additional PowerShell terminals, one command in each; leave them running:

```powershell
kubectl -n acit3495 port-forward svc/enter-data 5000:5000
```

```powershell
kubectl -n acit3495 port-forward svc/show-results 3000:3000
```

Then in the original terminal:

```powershell
python scripts/smoke_test_cloud.py
```

Browse `http://localhost:5000` and `http://localhost:3000`; log in as `student`. Your local demo password is at `secrets/demo_password.txt`. The test verifies login, CSRF, MySQL insertion, analytics refresh, MongoDB results and both frontends running on EKS.

**Optional public HTTP demo addresses:** only when explicitly required, apply `kubectl apply -f k8s/30-public-optional.yaml`. Then run `kubectl -n acit3495 get svc enter-data-public show-results-public` until both `EXTERNAL-IP`/hostnames appear. Configure the cross-app UI links:

```powershell
python scripts/set_public_links.py --enter http://ENTER-LB-ADDRESS --results http://RESULTS-LB-ADDRESS
python scripts/smoke_test_cloud.py --enter http://ENTER-LB-ADDRESS --results http://RESULTS-LB-ADDRESS
```

**WARNING:** Optional AWS external services use HTTP with no TLS, for disposable demo-only credentials and short-lived testing. Do not use real passwords. The default port-forward access is safer for coursework, and both frontends remain reachable from your workstation. Remove public exposure after demo: `kubectl delete -f k8s/30-public-optional.yaml`. For a production deployment, add real HTTPS/TLS, an ingress/controller and proper domain names.

## Step 6: Prove HPA really works using three controlled traffic levels

Keep the `enter-data` port-forward open. Verify HPA is serving CPU values:

```powershell
kubectl -n acit3495 get hpa auth-hpa
kubectl -n acit3495 get deployment auth
kubectl top pods -n acit3495 -l app=auth
```

Run **all three scenarios** automatically; this typically takes 17 minutes of configured load, plus small startup/teardown time:

```powershell
python scripts/run_experiments.py
python scripts/summarize_results.py
```

The runner launches actual k6 requests to the real application and simultaneously polls the Kubernetes HPA and resource Metrics API at 10-second intervals. It creates:

- `evidence/hpa-timeseries.csv`, the real timestamped replica/CPU metrics.
- `evidence/low-summary.json`, `increasing-summary.json`, `decreasing-summary.json`, plus console logs.
- `evidence/performance-summary.csv` and `evidence/measured-results.md`.
- Charts: `evidence/hpa-replicas.png`, `hpa-cpu.png`, `throughput.png`, `response-time.png`, `errors.png` (only when data exist).

**Scenarios:** low = 1 virtual user for 3 minutes, increasing = 1→12→36 virtual users with 7-minute total duration, decreasing = 1 virtual user for 7 minutes. The increasing phase uses real login password verification to load CPU in **auth**, then writes to MySQL and recalculates analytics in MongoDB. The decreasing phase is long enough to observe scale-in despite the 120-second HPA stabilization setting. If your environment does not scale out under this load, do not claim success: inspect HPA conditions, CPU, k6 failures, frontend/DB capacity, and tune **and repeat** the documented test while recording parameters.

For a live watch in an extra terminal:

```powershell
kubectl -n acit3495 get hpa auth-hpa -w
kubectl -n acit3495 get pods -l app=auth -w
```

## Step 7: Prepare measured report, presentation, and screenshots

```powershell
python scripts/create_report.py
python scripts/create_presentation.py
```

These programs use actual evidence files when present. Before cloud experiments, they show clear `NOT YET MEASURED` markers instead of fictional data. Take the seven screenshots listed in `docs/demo-script.md`, put them under `evidence/`, and add your **observed** comparison, timestamps and bottlenecks to the report/deck. You can export the final report to PDF in Word if your instructor wants PDF.

Open `docs/Technical_Report.docx`, `docs/Project2_Presentation.pptx`, `docs/architecture.png`, `docs/demo-script.md`, `docs/rubric-map.md`. The `docs/results-guide.md` explains each analysis question and how to interpret k6 vs CPU data.

## Step 8: Demo and cleanup (prevent AWS charges)

Use `docs/demo-script.md` during the demo. When grading is finished and you have saved all evidence, destroy the **entire project cluster**:

```powershell
eksctl delete cluster -f cloud/eksctl-cluster.yaml
```

This permanently deletes cluster resources and can destroy the database contents on their EBS volumes. Verify there are no leftover EBS volumes, LoadBalancers, and CloudFormation resources in AWS. Deleting your local project directory does NOT stop cloud billing.

## Assumptions / honest limitations

1. The included full Project 1 source is the prior `ACIT3495_Option1_Starter.zip` archive available from your saved files. If your team's actual private GitHub repository has newer code, reconcile the repo before pushing/deploying the four images.
2. AWS credentials, running cluster, GHCR access and real measurements are **not included** and cannot be fabricated in a ZIP.
3. EKS add-on IAM permissions and public LoadBalancer features vary by account. The optional public services require cloud LB support and should only be enabled briefly for the demo.
4. The current app uses individual synchronous analytics recalculation after writes. MySQL/MongoDB are single-replica stateful components, and HPA only scales auth; that can expose bottlenecks under heavy traffic, which is useful to discuss in the required analysis.
5. The source uses demo HTTP cookies with `COOKIE_SECURE=false` for local port forwarding. This package is for an academic test, not production security.
