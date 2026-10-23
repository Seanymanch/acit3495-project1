# ACIT 3495 Project 1 Technical Report

- Matthew, May, Sean
- Date: October 22, 2026
- Repository: https://github.com/Seanymanch/acit3495-project1

## 1. Architecture and functionality 
The user logs in through the Authentication Service, which validates their credentials. Once authenticated, the user submits temperature readings through the Enter Data application, which stores them in MySQL. The Analytics Service reads the data, calculates the minimum, maximum, average, and count, and saves the results in MongoDB. Finally, the Show Results application retrieves and displays the calculated statistics to the user.

MySQL is used to store the original temperature readings because it provides structured, persistent storage. MongoDB is used to store the calculated statistics separately, allowing the Show Results application to retrieve results without recalculating them every time. This separation also allows the data collection and analytics components to operate independently.

### Architecture Diagram

![architecture](/screenshots/architecture%20diagram.png)

- **Host-exposed**: only Enter Data on localhost:5000 and Show Results on localhost:3000.
- **Internal**: Auth, Analytics, MySQL, and MongoDB stay on private Docker networking.
- **Storage**: MySQL mysql_data; MongoDB mongo_data volumes.
- **Failure behavior**: If MongoDB is down while writing data, the raw reading remains in MySQL; analytics must be retriggered after MongoDB recovers.

## 2. Docker and optimization 

The Compose project defines six services:

| Service | Port(s) | Network(s) | Image / Dockerfile |
|---|---|---|---|
| MySQL | 3306 (internal only; not published) | `backend` | `mysql:8.4` official image; no project Dockerfile |
| MongoDB | 27017 (internal only; not published) | `backend` | `mongo:7.0` official image; no project Dockerfile |
| Authentication (`auth`) | 8000 (internal only; not published) | `backend` | Built from `auth/Dockerfile` |
| Analytics | 8000 (internal only; not published) | `backend` | Built from `analytics/Dockerfile` |
| Enter Data | `127.0.0.1:5000` → container 5000 | `frontend`, `backend` | Built from `enter-data/Dockerfile` |
| Show Results | `127.0.0.1:3000` → container 3000 | `frontend`, `backend` | Built from `show-results/Dockerfile` |

Only Enter Data and Show Results publish host ports, bound to localhost. The `backend` network is internal. The Show Results optimized Dockerfile uses two `node:22-alpine` stages: one to install production dependencies and one to assemble and run the application as a non-root user. The baseline comparison uses `show-results/Dockerfile.baseline`.

| Build | Image size | Build seconds | Notes |
|---|---:|---:|---|
| Node baseline | 1,590.7 MiB | 4.70 | `node:22` copies the full application context and installs production dependencies. |
| Node optimized | 243.6 MiB | 4.68 | Multi-stage `node:22-alpine` build copies only runtime files and production dependencies, and runs as a non-root user. |

Image sizes are from `docker image inspect`. Build times are uncached local measurements and may vary with the host and Docker environment.

The optimized Docker image reduced the image size from 1,590.7 MiB to 243.6 MiB. This was achieved using a smaller Alpine-based image and a multi-stage Dockerfile that only includes the files and dependencies needed at runtime. The build times remained nearly identical, but the smaller image needs less storage and is more efficient to distribute.

## 3. Security 
The application uses authentication to block unauthorized access and input validation to reject invalid temperature readings. Security is improved by restricting published ports to localhost, keeping databases on a private Docker network, running containers as non-root users, and excluding local secret files from Git. MongoDB users have restricted read/readWrite permissions.

Credentials are stored in local secret files that are excluded from Git to prevent accidental exposure. MongoDB user permissions are assigned based on their responsibilities to limit unnecessary database access. This reduces the risk of unauthorized access and protect application data.

Opening the application in a private or incognito browser will always require the user to log in again. An incorrect password attempt will redirect back to the login page.

For production use, the system would also need HTTPS, password reset functionality, and login rate limiting to improve security.

## 4. Reliability and persistence 

All six services use Docker health checks to monitor database availability and application responsiveness. MySQL and MongoDB use database ping checks, while the application services use HTTP health endpoints. Health checks help identify unavailable services, but don't guarantee that the entire application workflow is functioning correctly. During failure testing,  we stopped the database services and restarted them to verify recovery. If MongoDB becomes unavailable during an analytics update, another temperature submission is required after recovery to trigger recalculation of the stored statistics.

| Failure | Observed user impact | How restored |
|---|---|---|
| MySQL stopped | Login request failed when the database was stopped | `docker compose start mysql;` |
| MongoDB stopped | Login to Show Results page failed | `docker compose start mongo;` |

Database persistence was tested by recreating the MySQL and MongoDB containers without deleting their Docker volumes. After recreation, the previously entered temperature readings and calculated statistics remained available, confirming that data is stored persistently.

## 5. Performance and observability

We tested performance with 10 simulated users and 100 requests using a load testing script and authentication. The performance was measured using throughput, error count, average response latency, and live CPU and memory usage using the `docker stats` command. Results are below.

| Configuration | Requests | Throughput req/s | Errors | Mean latency s | CPU | RAM |
|---|---:|---:|---:|---:|---:|---|
| Python aggregation, pool 1 | 100 | 9.49/s | 0 | 1.03s | 0.42% | 13.07% |
| SQL aggregation, pool 5 | 100 | 8.87/s | 0 | 1.11s | 0.87% | 61.28% |

CPU and RAM scores are snapshots from during the tests and may not reflect true performance.

## 6. CI/CD 

Our project uses GitHub Actions to automate the CI/CD process. The pipeline runs automated tests, builds Docker images, and performs Trivy vulnerability scans. Successfully built images are tagged and pushed to GitHub Container Registry (GHCR). We verified the published images using `docker buildx imagetools inspect` to confirm they both support AMD64 and ARM64 architectures.

Automating the CI/CD pipeline helps identify problems before deployment and ensures Docker images are tested and scanned consistently. Multi-architecture images allow the application to run on both AMD64 and ARM64 systems without requiring separate builds.

## 7. Limitations and next improvements

The analytics service only updates when new data is submitted and does not automatically retry after a failure. Adding a queue or scheduler would improve reliability. For production use, the system would also need HTTPS, password reset functionality, and login rate limiting to improve security.
