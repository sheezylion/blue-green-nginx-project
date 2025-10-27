# Blue-Green Deployment with Nginx Auto-Failover

This project implements a Blue-Green deployment pattern with automatic failover using Nginx as a reverse proxy.

When Blue fails, Nginx automatically routes traffic to Green with zero client-side errors.

### Prerequisites

- Docker installed
- Docker Compose installed
- The Blue and Green Docker images (provided by instructor)
