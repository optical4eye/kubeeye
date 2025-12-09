# KubeEye - Kubernetes Cluster Inspection Tool

This version of kubeeye is located here - https://github.com/optical4eye/kubeeye/

## Overview

KubeEye is a **purely observational** Kubernetes cluster inspection tool focused on safe information gathering about the cluster and identifying potential issues. The tool provides a modern React web interface with FastAPI backend, supporting various inspection methods.

**Version 3.0** introduces a microservices architecture with separate frontend and backend components for better scalability and maintainability.

**Security Guarantee**: KubeEye uses a strict read-only inspection policy, all operations are limited to information gathering and status viewing, no modifications, deletions, or dangerous operations are ever performed, ensuring cluster security.

## Main Features

- **Security First**: Mandatory read-only mode, all inspection commands undergo strict security checks, ensuring zero risk
- **Cluster Information Management**: Support for configuring and managing connection information for multiple clusters
- **Various Inspection Methods**: Node status, Prometheus metrics, OPA rule compliance
- **Visual Reports**: Intuitive display of inspection results, including charts and detailed problem descriptions
- **History Query**: Support for viewing inspection result history and trend analysis
- **Fix Recommendations**: Providing solution recommendations for detected problems
- **Sensitive Information Encryption**: Protection of cluster connection passwords and other sensitive information using encryption algorithms
- **Log Management**: Unified logging system for convenient tracking and problem diagnostics
- **Certificate Monitoring**: Automatic checking of kubeconfig certificate expiration dates, advance warnings

## Security Features

### Purely Observational Design
- **Read-Only Principle**: All inspection operations are limited to information retrieval and status viewing
- **Whitelist Mode**: Only explicitly safe commands are allowed to execute, all unknown commands are prohibited by default
- **Multi-Level Security Checks**: Strict security checks before command execution
- **Audit Log**: Complete recording of all operations and security events

### Security Measures
- **Modification Operation Ban**: Dangerous commands such as `rm`, `chmod`, `systemctl restart`, etc. are prohibited
- **Write Operation Ban**: No write actions are allowed, such as file redirection, file creation, etc.
- **Installation Operation Ban**: Software installation such as `apt install`, `pip install`, etc. is not allowed
- **Mandatory Safe Mode**: It is impossible to lower security levels through settings

## Architecture

### Version 3.0 - Microservices Architecture

- **Frontend**: React application served by Nginx
- **Backend**: FastAPI application with business logic
- **Database**: File-based storage (JSON files)
- **Communication**: REST API between frontend and backend

### Components

```
┌─────────────────┐    REST API    ┌─────────────────┐
│   React Frontend│◄──────────────►│  FastAPI Backend │
│     (Nginx)     │                │   (Python)      │
└─────────────────┘                └─────────────────┘
         │                                   │
         └────────────► Browser ◄────────────┘
```

## Quick Start

### Method 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/optical4eye/kubeeye.git
cd kubeeye

# Start services
docker-compose up -d

# Access application at http://localhost
```

### Method 2: Separate Docker Images

```bash
# Build frontend
docker build -f Dockerfile.frontend -t kubeeye-frontend:v3.0 .

# Build backend
docker build -f Dockerfile.backend -t kubeeye-backend:v3.0 .

# Run backend
docker run -d \
  --name kubeeye-backend \
  -p 8000:8000 \
  -v kubeeye-data:/app/data \
  kubeeye-backend:v3.0

# Run frontend
docker run -d \
  --name kubeeye-frontend \
  -p 80:80 \
  -e REACT_APP_API_URL=http://localhost:8000 \
  kubeeye-frontend:v3.0
```

### Method 3: Kubernetes with Helm

```bash
# Add Helm repository (if applicable)
# helm repo add kubeeye https://optical4eye.github.io/kubeeye

# Install with Helm
helm install kubeeye ./chart/kubeeye

# Access via NodePort (default: 30693)
# Or configure Ingress for domain access
```

### Method 4: Development Mode

```bash
# Backend
cd /path/to/kubeeye
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8000 --reload

# Frontend (new terminal)
cd frontend
npm install
npm start
# Access at http://localhost:3000 (proxies to backend)
```