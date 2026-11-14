# ACIT 3495 Project 1 Technical Report

Author(s): [names]
Date: [date]
Repository: [GitHub repository URL]

## 1. Architecture and functionality (15 marks)
Explain flow from login to storage to calculation to display. Insert `architecture.md` diagram. Include screenshots of two web apps with real calculated outputs.

## 2. Docker and optimization (15 marks)
List six services, ports, networks, Dockerfiles, and multi-stage build. Include two `Measure-Command` output screenshots and `docker image ls` results.

| Build | Image size | Build seconds | Notes |
|---|---:|---:|---|
| Node baseline | [measure] | [measure] | Full Node image |
| Node optimized | [measure] | [measure] | Multi-stage Alpine + ignored files |

## 3. Security (15 marks)
Show blocked unauthenticated access and invalid input; the localhost-only published ports; private databases and network; non-root `id` output; local secret files ignored by Git; scoped Mongo read/readWrite users; and Trivy scan results. Record any scan CVEs and planned fixes. State that public deployment needs HTTPS, secure cookies, and login rate limits.

## 4. Reliability and persistence (10 marks)
List health checks and their coverage. Show readings before/after database container recreation **without removing volumes**. Document two failures and actual logs, impact, recovery commands, and any manual refresh step.

| Failure | Observed user impact | Container/log evidence | How restored |
|---|---|---|---|
| MySQL stopped | [observe] | [image] | [record] |
| MongoDB stopped | [observe] | [image] | [record] |

## 5. Performance and observability (10 marks)
Explain test: same user count, number of requests, host environment, login method, measurement timing, and dataset size. Compare two changes (SQL-side aggregation; database pool size). Include live-load `docker stats`, throughput, errors, latency, and anonymized logs.

| Configuration | Requests | Throughput req/s | Errors | Mean latency s | CPU | RAM |
|---|---:|---:|---:|---:|---:|---|
| Python aggregation, pool 1 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |
| SQL aggregation, pool 5 | [ ] | [ ] | [ ] | [ ] | [ ] | [ ] |

Note possible measurement bias if dataset size or background load differs. Never claim an improvement without supporting numbers.

## 6. CI/CD (10 marks)
Include successful Actions test/build/Trivy/tag/push outputs; links to GHCR images; `docker buildx imagetools inspect` output showing amd64 and arm64.

## 7. Demonstration/defense (25 marks)
Explain security tradeoffs, the role of each container, why two databases are required, how recovery works, and which parts are not production-ready.

## 8. Limitations and next improvements
Explain that analytics refresh is triggered by submissions and is not retried automatically after an outage; add queue/scheduler for more resilience. Explain that password reset, HTTPS and login rate limiting would be needed outside localhost.
