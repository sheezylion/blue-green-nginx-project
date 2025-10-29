# Blue-Green Deployment with Nginx Auto-Failover

This project implements a Blue-Green deployment pattern with automatic failover using Nginx as a reverse proxy.

When Blue fails, Nginx automatically routes traffic to Green with zero client-side errors.

### Prerequisites

- Docker installed
- Docker Compose installed
- The Blue and Green Docker images (provided by instructor)

## Setup Instructions

1.  Clone/Create Project Structure

```
mkdir blue-green-nginx && cd blue-green-nginx
mkdir nginx
```

2. Configure Environment Variables

Copy .env.example to .env:

```
cp .env.example .env
```

Edit .env and update the image URLs:

```
BLUE_IMAGE=your-actual-image-url:blue
GREEN_IMAGE=your-actual-image-url:green
ACTIVE_POOL=blue
RELEASE_ID_BLUE=v1.0.0-blue
RELEASE_ID_GREEN=v1.0.0-green
```

3.  Start Services

```
docker-compose up -d
```
<img width="1028" height="504" alt="Screenshot 2025-10-27 at 13 43 03" src="https://github.com/user-attachments/assets/e82822b6-13ec-4790-b774-4eba1fcc3999" />

Check all services are running:

```
docker-compose ps
```

<img width="1008" height="166" alt="Screenshot 2025-10-27 at 13 43 24" src="https://github.com/user-attachments/assets/23179bd0-5ad4-4427-9bdc-d9479c3fdaab" />

### Testing the Deployment

Baseline Test (Blue Active)

```
# Check that traffic goes to Blue
curl -i http://localhost:8080/version

# Expected headers:
# X-App-Pool: blue
# X-Release-Id: v1.0.0-blue
```
<img width="640" height="224" alt="Screenshot 2025-10-27 at 15 16 09" src="https://github.com/user-attachments/assets/660fe19b-3c77-46e7-b50a-09fd0661096d" />


### Test Automatic Failover

1. Induce chaos on Blue:

```
curl -X POST "http://localhost:8081/chaos/start?mode=timeout"
```

2. Verify immediate switch to Green:

```
curl -i http://localhost:8080/version
```

<img width="831" height="383" alt="Screenshot 2025-10-27 at 15 20 25" src="https://github.com/user-attachments/assets/ed4ae91c-1cd0-4b75-aacc-f3e88b0ad348" />

3. Stop chaos and verify switch back to Blue:

```
# Stop chaos
curl -X POST http://localhost:8081/chaos/stop

# Wait a few seconds for health checks to pass
sleep 10

# Verify Blue is active again
curl -i http://localhost:8080/version
```
<img width="868" height="349" alt="Screenshot 2025-10-27 at 15 23 18" src="https://github.com/user-attachments/assets/6b784e2f-e47c-4a94-96c4-7e5fff5bcf41" />

The script will:

- Verify Blue is active initially
- Trigger chaos on Blue
- Verify automatic failover to Green
- Test stability (20 requests, should be ≥95% success)
- Stop chaos and verify recovery


