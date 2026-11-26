#!/usr/bin/env python3
"""Rebuild recovery test database with multi-tenant schema."""

import os
import sys

os.environ['TEST_DATABASE_URL'] = 'postgresql://recovery_test_user:recovery_test_pass_7XqR9kL2mN4@localhost:5433/neoeve_recovery_test'

try:
    from sqlalchemy import create_engine, text
    from backend.database.models import Base

    db_url = os.environ.get('TEST_DATABASE_URL')
    print(f"[INFO] Database URL: {db_url}")

    engine = create_engine(db_url)

    print('[INFO] Dropping old tables...')
    Base.metadata.drop_all(engine)
    print('[INFO] Old tables dropped.')

    print('[INFO] Creating new schema with tenant_id multi-tenant...')
    Base.metadata.create_all(engine)
    print('[INFO] New schema created successfully!')

    # Verify projection_checkpoints structure
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name='projection_checkpoints'
            ORDER BY ordinal_position
        """))
        cols = result.fetchall()
        print(f'\n[INFO] projection_checkpoints columns:')
        for col in cols:
            null_str = col[2] if col[2] else 'NO '
            print(f'  ✓ {col[0]:<25} {col[1]:<20} null={null_str:<5} default={col[3]}')

        # Check primary key
        result = conn.execute(text("""
            SELECT constraint_name, column_name
            FROM information_schema.key_column_usage
            WHERE table_name='projection_checkpoints' AND constraint_name LIKE '%pkey'
            ORDER BY ordinal_position
        """))
        pk_cols = result.fetchall()
        print(f'\n[INFO] Primary Key:')
        for col in pk_cols:
            print(f'  ✓ {col[1]} (constraint: {col[0]})')

    print('\n✅ Database rebuild complete!')
    sys.exit(0)

except Exception as e:
    print(f'❌ ERROR: {e}', file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
