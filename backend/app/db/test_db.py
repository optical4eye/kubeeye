#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple database connectivity test - Async Only
"""

import asyncio
from db.database import get_db, init_database
from db.repositories.inspection_result_repository import InspectionResultRepository
from db.repositories.cluster_repository import ClusterRepository
from db.repositories.schedule_repository import ScheduleRepository


async def test_database_connection():
    """Test database connection and basic operations"""
    print("Testing database connection...")

    try:
        # Initialize database
        print("Initializing database...")
        await init_database()
        print("✅ Database initialized successfully")

        # Test repositories
        async for db in get_db():
            # Test inspection results repository
            print("Testing inspection results repository...")
            repo = InspectionResultRepository(db)
            count = await repo.count()
            print(f"✅ Inspection results repository works. Current count: {count}")

            # Test cluster repository
            print("Testing cluster repository...")
            cluster_repo = ClusterRepository(db)
            clusters = await cluster_repo.get_all_names()
            print(f"✅ Cluster repository works. Current clusters: {clusters}")

            # Test schedule repository
            print("Testing schedule repository...")
            schedule_repo = ScheduleRepository(db)
            tasks = await schedule_repo.get_enabled_tasks()
            print(f"✅ Schedule repository works. Current tasks: {len(tasks)}")

            print("\n🎉 All database tests passed!")
            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    asyncio.run(test_database_connection())
