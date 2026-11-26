#!/usr/bin/env python3
"""Setup recovery test database schema."""

import os
import sys

os.environ['TEST_DATABASE_URL'] = 'postgresql://recovery_test_user:recovery_test_pass_7XqR9kL2mN4@localhost:5433/neoeve_recovery_test'

try:
    from sqlalchemy import create_engine, text
    from backend.database.models import Base

    db_url = os.environ.get('TEST_DATABASE_URL')
    print(f"[INFO] Database URL: {db_url}")

    engine = create_engine(db_url)

    print('[INFO] Creating all tables...')
    Base.metadata.create_all(engine)
    print('[INFO] Tables created successfully!')

    # Verify
    with engine.connect() as conn:
        result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = result.fetchall()
        print(f'[INFO] Found {len(tables)} tables:')
        for table in tables:
            print(f'  ✓ {table[0]}')

    print('\n✅ Database setup complete!')
    sys.exit(0)

except Exception as e:
    print(f'❌ ERROR: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
