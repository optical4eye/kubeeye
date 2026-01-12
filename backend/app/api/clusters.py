#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cluster management routes

Этот файл экспортирует роутер для работы с кластерами.
Бизнес-логика находится в services/cluster_service.py,
API endpoints - в controllers/cluster_controller.py.
"""

from api.controllers.cluster_controller import router as cluster_router

# Экспортируем роутер для использования в main.py
router = cluster_router
