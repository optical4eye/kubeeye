#!/bin/bash

# Stop and remove all containers, then start fresh
# This ensures LDAP data is recreated on each run
docker-compose down -v
docker-compose up -d

# Rebuild and recreate backend and frontend
docker compose up --build --force-recreate --no-deps backend -d
docker compose up --build --force-recreate --no-deps frontend -d
