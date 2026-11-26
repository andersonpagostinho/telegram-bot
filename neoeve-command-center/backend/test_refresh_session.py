#!/usr/bin/env python3
"""Direct test of create_refresh_session to find the error."""

import logging
from database.connection import SessionLocal
from app.services.refresh_token_service import create_refresh_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

db = SessionLocal()
try:
    user_id = "5e6ec06f-e96d-4b1e-a37c-98253c1789b2"
    tenant_id = "3b38df6a-429d-49b0-9d92-9d2ea8476788"

    logger.info("Testing create_refresh_session() directly...")
    session_id, refresh_token = create_refresh_session(
        db,
        user_id=user_id,
        tenant_id=tenant_id,
        user_agent="Test Agent",
        ip_address="127.0.0.1",
    )

    logger.info(f"✅ Success! session_id={session_id}")
    logger.info(f"✅ Refresh token generated (length: {len(refresh_token)})")

except Exception as e:
    logger.error(f"❌ Exception: {type(e).__name__}", exc_info=True)
    logger.error(f"Error message: {str(e)}")
finally:
    db.close()
