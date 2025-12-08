# KubeEye - Kubernetes Cluster Inspection Tool

This version of kubeeye is located here - https://github.com/optical4eye/kubeeye/

## Overview

KubeEye is a **purely observational** Kubernetes cluster inspection tool focused on safe information gathering about the cluster and identifying potential issues. The tool is built on Streamlit and provides an intuitive web interface supporting various inspection methods.

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

## Quick Start

### Method 1: Run via Docker

#### Data Persistence
```bash
# Create data directory
mkdir -p /opt/kubeeye/data

# Run container with data directory and time mounting
docker run -d \
  --name kubeeye \
  -p 8501:8501 \
  -v /opt/kubeeye/data:/app/data \
  -v /etc/localtime:/etc/localtime:ro \
  kubespheredev/kubeeye:v2.0.0-alpha.1