# ACIT 3495 Project 1: Data Collection and Analytics System

A six-container, two-language microservices project for recording temperature readings, computing statistics, and showing the results through authenticated web apps.

**Status:** Starter implementation. Python/JavaScript syntax and unit tests were checked when packaged; **Docker could not be run in the packaging environment**, so you must run and verify the stack locally before claiming the working demo or screenshots.

## 0. Prerequisites

On **Windows**, install Docker Desktop (WSL2 backend), Git, Python 3.12+, Node.js 22 (optional if only using Docker), and VS Code. Docker Desktop must be running in **Linux containers** mode. Ensure you have sufficient RAM for MySQL and MongoDB (4 GB available is a useful starting point).

Open the extracted `ACIT3495_Option1_Starter` folder in VS Code, then **Terminal > New Terminal**. The steps below assume PowerShell with the terminal already in the project root. Run each command in order.

```powershell
python --version
docker --version
docker compose version
git --version
```

## 1. Understand the services

| Container | Technology | Purpose | Public port |
|---|---|---|---|
| enter-data | Python Flask + Gunicorn | Authenticated entry form, inserts reading into MySQL | localhost:5000 |
| auth | Python FastAPI + JWT | Validates login and tokens, hashes seeded user password | None |
| analytics | Python FastAPI | Calculates minimum, maximum, average, count; stores snapshot in MongoDB | None |
| show-results | Node.js + Express | Authenticated results page reads MongoDB | localhost:3000 |
| mysql | MySQL 8.4 | Persists user account and readings | None |
| mongo | MongoDB 7 | Persists aggregate snapshot | None |

The two web apps separately log in through the internal auth service. Submitting a temperature commits the reading to MySQL, then triggers internal analytics recalculation. Analytics writes one document to MongoDB. MongoDB has a write-capable analytics account and read-only results account. The API containers and databases are not published to the host. All secrets are mounted via Compose secrets, and application containers use unprivileged users.

## 2. Create secrets and start the stack

**Never add `secrets/*.txt` to Git, screenshots, or your submission.** Generate unique local credentials:

```powershell
python scripts/generate_secrets.py
```

The script creates missing files but preserves existing ones. Do **not** regenerate secrets after setting up volumes, because databases still contain the old credentials.

Build and start:

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Look for six containers with a healthy status after startup. On slower PCs databases may need a little time to initialize. If something is unhealthy:

```powershell
docker compose logs --tail=80 mysql
docker compose logs --tail=80 mongo
docker compose logs --tail=80 auth
docker compose logs --tail=80 analytics
docker compose logs --tail=80 enter-data
docker compose logs --tail=80 show-results
```

Read the **local demo password** privately. Never photograph the password:

```powershell
Get-Content .\secrets\demo_password.txt
```

Demo username: `student`. Enter that password when the login form prompts for it.

## 3. Run the application from beginning to end

1. Open http://localhost:5000 (Enter Data).
2. Log in with username `student` and the password you read from your local secret file.
3. Add the temperatures `10`, `20`, `30`, `40`, `50` individually. Each time select **Save reading**.
4. Confirm the page lists the saved readings and acknowledges the analytics refresh.
5. Open http://localhost:3000 (Show Results) and log in with the same credentials.
6. Confirm `count = 5`, `minimum = 10.00`, `maximum = 50.00`, `average = 30.00` (provided the MySQL volume started empty).
7. Take screenshots of the data-entry form and analytics page (excluding credentials).

**Reminder:** If you have previous readings in your persistent volume, statistics are for **all readings**, not only these five.

## 4. Run automated tests

Pure calculation unit tests (can run without Docker):

```powershell
python -m unittest discover -s tests -v
```

Node unit tests (requires local Node.js 22):

```powershell
cd show-results
npm test
cd ..
```

Integration smoke test for running containers (requires Python requests):

```powershell
python -m pip install requests
python scripts/smoke_test.py
```

The smoke test asserts that unauthenticated users get login redirects, signs in with a demo account, submits one reading, signs into the results service, and checks the displayed statistics. **This adds a reading**, so after the smoke test the count changes.

For additional protection evidence: open http://localhost:3000 in a private/incognito window and confirm the results require login. Enter an incorrect password. Attempt `-999` in the form and verify the browser rejects it; the backend also enforces the temperature range. Keep screenshots of the denied access/error, without displaying passwords.

## 5. Check architecture, exposure, secrets, and least privilege

```powershell
docker compose ps
docker compose config --services
docker network ls
docker compose exec enter-data id
docker compose exec show-results id
```

Only `5000` and `3000` should be published, and both are bound to local loopback (127.0.0.1). MySQL port 3306, MongoDB port 27017, and the internal HTTP ports should **not** be host-published. The `backend` Docker network is marked `internal: true` and the web apps communicate with backend services through Docker DNS.

Use your `compose.yaml` and the non-root `id` output as evidence. Secrets are in ignored local files mounted at `/run/secrets` only for services that need them. The root Mongo user is not used by the application services. The MySQL application user is database-specific (not root), although finer table-by-table MySQL privileges could strengthen it further.

**Important:** This HTTP configuration is for a local classroom demo. Do not expose the two web ports to the public internet without HTTPS, `COOKIE_SECURE=true`, and an appropriate reverse proxy. Login endpoints are not rate-limited, so do not treat this starter as an internet production deployment.

## 6. Test persistence (screenshots)

Add readings and confirm results first. Then recreate the stateful containers **without removing volumes**:

```powershell
docker compose up -d --force-recreate mysql mongo
docker compose up -d
docker compose ps
```

Log in again and verify the same readings and statistics still exist. This demonstrates `mysql_data` and `mongo_data` named volumes. Screenshot before/after pages and `docker compose ps`.

**Do not run `docker compose down -v` for persistence testing.** That command deletes named-volume data.

## 7. Two repeatable service failure tests

**Test A: MySQL failure**

```powershell
docker compose stop mysql
docker compose ps
```

Visit http://localhost:5000/ while logged in. The site may show dependency failure, login redirects, or a temporary error depending on token verification. Check service health and errors. Restart MySQL:

```powershell
docker compose start mysql
docker compose ps
```

Revisit the app and verify you can add readings after recovery. Restart any dependent app if it has not recovered yet: `docker compose restart auth analytics enter-data`.

**Test B: MongoDB failure**

```powershell
docker compose stop mongo
docker compose ps
```

Visit http://localhost:3000/ and observe the error or unavailable results. The data-entry app should still be able to save to MySQL even though refreshing analytics can fail. Restart:

```powershell
docker compose start mongo
docker compose ps
```

After recovery, **submit one more reading** at http://localhost:5000/ to trigger recalculation and confirm results become current. A write made during a Mongo outage is kept in MySQL; analytics is **not automatically retried** until the next submission. Document this limitation and improvement idea (a durable queue/background worker).

For each failure: screenshot `ps`, user-visible symptom, diagnostic logs, restart, and successful recovery.

## 8. Dockerfile optimization before and after

An intentionally basic Node Dockerfile and a multi-stage Alpine Node Dockerfile are included. On Windows PowerShell:

```powershell
Measure-Command { docker build --no-cache -f show-results/Dockerfile.baseline -t show-results:baseline show-results }
Measure-Command { docker build --no-cache -f show-results/Dockerfile -t show-results:optimized show-results }
docker image ls show-results
```

Take screenshots of elapsed times and image sizes. Repeat each build 2–3 times, consider network download/cache noise, and report the actual measured times. The baseline uses full Debian Node and copies sources before installing; the optimized version has dependency/runtime stages, Node Alpine, `.dockerignore` and non-root execution. **Smaller size is expected, but the build time improvement is not guaranteed** on the first build because of network/emulation effects.

## 9. Image vulnerability scanning

The GitHub Actions workflow runs Trivy on all four app images automatically. For a local CLI run if Trivy is installed:

```powershell
trivy image --severity HIGH,CRITICAL show-results:optimized
```

Keep the output, record vulnerabilities and affected packages, update dependencies or base images as needed, and explain any findings you cannot immediately fix. The included CI scan currently **reports** findings but does not fail the pipeline (`exit-code: '0'`); decide whether your instructor expects a hard-fail gate. A scan is evidence, not proof that an image is vulnerability-free.

## 10. Performance tests and two improvements

Use the included repeatable load generator. It authenticates once per worker (per thread), reuses HTTP sessions, and repeatedly submits readings. It is not a replacement for a professionally calibrated load test, but meets the basic request-throughput/error comparison.

```powershell
python -m pip install requests
```

**Baseline:** compare Python-side aggregation and a pool size of 1. Set environment variables in this PowerShell session:

```powershell
$env:ANALYTICS_MODE = "python"
$env:DB_POOL_SIZE = "1"
docker compose up -d --force-recreate analytics enter-data
python scripts/quick_load.py --users 10 --requests 100
docker stats --no-stream
```

**Optimized:** use SQL aggregation, which avoids transferring every reading to Python, and a database connection pool of 5 for concurrent requests:

```powershell
$env:ANALYTICS_MODE = "sql"
$env:DB_POOL_SIZE = "5"
docker compose up -d --force-recreate analytics enter-data
python scripts/quick_load.py --users 10 --requests 100
docker stats --no-stream
```

Take screenshots and record throughput, total time, errors, CPU, and memory for each test. For a fairer comparison, bring each run back to an identical seed dataset and similar host load. The second run above has more stored readings than the first, so it is an **initial exploration**, not a controlled benchmark. You can repeat on two separate fresh environments, using `docker compose down -v` **only if you intentionally want to erase all current project data**. Never include the local secrets in test reports.

The two changes under evaluation are (1) moving aggregates into MySQL (`MIN/MAX/AVG/COUNT` instead of fetching all rows), and (2) increasing connection-pool capacity for concurrency. **Report measured results, including if an improvement did not help**. More connections can worsen resource pressure under some workloads. Screenshot Docker CPU/memory readings while the load test is running to capture **load-time**, not just idle, utilization.

For optional JMeter evidence, create an HTTP Test Plan for `localhost:5000` using Cookie Manager, a login POST sampler, a CSS/regex extractor for the hidden `csrf` field on the home page, and a `/submit` POST sampler with `${csrf}` and temperature values. Capture Summary Report throughput/error percentage alongside `docker stats` output.

When finished with environment variables:

```powershell
Remove-Item Env:ANALYTICS_MODE
Remove-Item Env:DB_POOL_SIZE
docker compose up -d --force-recreate analytics enter-data
```

## 11. Git repository and CI/CD publishing

Create a new **private GitHub repository** named `acit3495-project1` (an empty repo is easiest). Then, from your local project root:

```powershell
git init
git branch -M main
git add .
git status
```

**Check `git status` carefully:** none of the `.txt` files under `secrets/` should be staged. If a secret is staged, stop and unstage it before committing.

```powershell
git commit -m "Build containerized temperature analytics system"
git remote add origin https://github.com/YOUR_USERNAME/acit3495-project1.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your own GitHub account name. Authenticate using the GitHub credential manager or an approved Git workflow, not a password typed into your command or committed to a file. GitHub Actions starts on your first push to `main`; click **GitHub repository > Actions > ACIT3495 Tests Build Scan Publish**.

The workflow:
1. Runs Python and Node unit tests.
2. Builds all four Docker app images.
3. Scans each app image with Trivy.
4. Logs in to GitHub Container Registry using the built-in `GITHUB_TOKEN` and `packages: write` permission (no personal access token is needed for this workflow).
5. Builds AMD64 and ARM64 images using QEMU/Buildx.
6. Publishes `latest` and full Git commit SHA tags for all four app images to `ghcr.io/<youraccount>/acit3495-<service>`.

Use the successful workflow and your repository's **Packages** page as screenshot evidence. New GHCR packages can initially be private. You do **not** have to make your source repository public. Ensure GitHub Actions has permission to create packages in your account/organization; if package publication is denied, check repository Actions permissions and the package linkage. The workflow intentionally does **not** deploy the application to a public server.

To verify one published image's architectures after successful publishing:

```powershell
docker buildx imagetools inspect ghcr.io/YOUR_USERNAME/acit3495-enter-data:latest
```

If your GitHub username has uppercase characters, use the lowercase registry namespace in the command.

## 12. Demonstration and hand-in

Present this workflow:
1. Explain architecture: app entry → MySQL → analytics → MongoDB → results.
2. Log in to both web apps and show access protection.
3. Submit readings and verify min/max/average/count.
4. Demonstrate database privacy, non-root containers, ignored secrets.
5. Show named volumes, health checks, and recovery evidence.
6. Show optimization before/after results, image scan, and load test.
7. Open the passing CI/CD workflow and GHCR multiarch image listing.

Submit the Git repo containing `compose.yaml`, app source, Dockerfiles, tests, CI workflow, architecture diagram, and this README. Write the technical report using `docs/technical-report-template.md` and include your **actual** screenshots/measurements. Do not make up successful results. The package includes a simple architecture diagram in `docs/architecture.md`.

### Cleanup

Stop but keep data:

```powershell
docker compose down
```

To destroy all **project** database volumes, only when you no longer need your saved data/evidence:

```powershell
docker compose down -v
```

### Common issues

- **Docker command not found:** install/start Docker Desktop; reopen terminal.
- **mysql or mongo unhealthy:** inspect their logs and make sure enough memory is available.
- **Port 5000/3000 already in use:** close the conflicting local service or change only the host side of the port mapping.
- **Login works once, then fails after changing password file:** the password hash in MySQL and databases do not update just because a local secret file changed. Restore the original secrets or intentionally reset data.
- **Stats are stale:** if MongoDB went down during insertion, submit another reading to trigger recalculation. Do not claim automatic replay/recovery.
- **No package after CI:** examine GitHub Actions `packages: write`, event/branch, and the publish step. PR builds do not publish.
