#!/bin/bash

docker-compose up -d

docker compose up --build --force-recreate --no-deps backend -d

docker compose up --build --force-recreate --no-deps frontend -d
