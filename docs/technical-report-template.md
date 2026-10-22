# ACIT 3495 Project 1 Technical Report

Author(s): [names]
Date: [date]
Repository: [GitHub repository URL]

## 1. Architecture and functionality (15 marks)
The user logs in through the Authentication Service, which validates their credentials. Once authenticated, the user submits temperature readings through the Enter Data application, which stores them in MySQL. The Analytics Service reads the data, calculates the minimum, maximum, average, and count, and saves the results in MongoDB. Finally, the Show Results application retrieves and displays the calculated statistics to the user.
Insert `architecture.md` diagram. Include screenshots of two web apps with real calculated outputs.

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

## 7. Limitations and next improvements

The analytics service only updates when new data is submitted and does not automatically retry after a failure. Adding a queue or scheduler would improve reliability. For production use, the system would also need HTTPS, password reset functionality, and login rate limiting to improve security.
