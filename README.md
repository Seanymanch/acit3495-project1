# ACIT 3495 Project 1: Data Collection and Analytics System

A six-container, two-language microservices project for recording temperature readings, computing statistics, and showing the results through authenticated web apps.

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

Generate unique local credentials:

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

Get the password:

```powershell
Get-Content .\secrets\demo_password.txt
```

Demo username: `student`. Enter that password when the login form prompts for it.

## 3. Run the application from beginning to end

1. Open http://localhost:5000 and enter a temperature.
2. Log in with username `student` and the password you read from your local secret file.
3. Add the temperatures `10`, `20`, `30`, `40`, `50` individually. Each time select **Save reading**.
4. Confirm the page lists the saved readings and acknowledges the analytics refresh.
5. Open http://localhost:3000 (Show Results) and log in with the same credentials.

If you have previous readings in your persistent volume, statistics are for **all readings**, not only these five.

## 4. Run automated tests

Calculation unit tests:

```powershell
python -m unittest discover -s tests -v
```

Node unit tests:

```powershell
cd show-results
npm.cmd test
cd ..
```

Integration test for running containers:

```powershell
python -m pip install requests
python scripts/smoke_test.py
```

The smoke test asserts that unauthenticated users get login redirects, signs in with a demo account, submits one reading, signs into the results service, and checks the displayed statistics.

For additional protection evidence: open http://localhost:3000 in a private/incognito window and confirm the results require login. Enter an incorrect password. Attempt `-999` in the form and verify the browser rejects it; the backend also enforces the temperature range. Keep screenshots of the denied access/error, without displaying passwords.

## 5. Test persistence

Add readings and confirm results first. Then recreate the stateful containers **without removing volumes**:

```powershell
docker compose up -d --force-recreate mysql mongo
docker compose up -d
docker compose ps
```

Log in again and verify the same readings and statistics still exist. This demonstrates `mysql_data` and `mongo_data` named volumes. Screenshot before/after pages and `docker compose ps`.

**Do not run `docker compose down -v` for persistence testing.** That command deletes named-volume data.

## 6. Two repeatable service failure tests

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

Visit http://localhost:3000/ to see the error or unavailable results. The data-entry app should still be able to save to MySQL even though refreshing analytics can fail. Restart:

```powershell
docker compose start mongo
docker compose ps
```

After recovery, **submit one more reading** at http://localhost:5000/ to trigger recalculation and confirm results become current. A write made during a Mongo outage is kept in MySQL; analytics is **not automatically retried** until the next submission. Document this limitation and improvement idea (a durable queue/background worker).

## 7. Image vulnerability scanning

The GitHub Actions workflow runs Trivy on all four app images automatically. For a local CLI run if Trivy is installed:

```powershell
trivy image --severity HIGH,CRITICAL show-results:optimized
```


## 8. Performance tests

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

## 9. Git repository and CI/CD publishing

The workflow:
1. Runs Python and Node unit tests.
2. Builds all four Docker app images.
3. Scans each app image with Trivy.
4. Logs in to GitHub Container Registry using the built-in `GITHUB_TOKEN` and `packages: write` permission (no personal access token is needed for this workflow).
5. Builds AMD64 and ARM64 images using QEMU/Buildx.
6. Publishes `latest` and full Git commit SHA tags for all four app images to `ghcr.io/<youraccount>/acit3495-<service>`.

To verify one published image's architectures after successful publishing:

```powershell
docker buildx imagetools inspect ghcr.io/YOUR_USERNAME/acit3495-enter-data:latest
```

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
