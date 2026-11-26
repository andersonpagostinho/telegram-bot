#!/usr/bin/env python3
"""Direct test of login function to see what's happening."""

import logging
from database.connection import SessionLocal
from app.services.auth_service import login

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    logger.info("Testing login() directly...")
    result, error = login(db, "admin@test.com", "Admin123!")

    logger.info(f"Result: {result}")
    logger.info(f"Error: {error}")

    if result:
        logger.info(f"Result keys: {list(result.keys())}")
        logger.info(f"Single tenant: {result.get('single_tenant')}")
        logger.info(f"User ID: {result.get('user_id')}")
        logger.info(f"Tenant ID: {result.get('tenant_id')}")

except Exception as e:
    logger.error(f"Exception: {type(e).__name__}: {str(e)}", exc_info=True)
finally:
    db.close()
