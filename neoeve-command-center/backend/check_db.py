from database.connection import SessionLocal
from database.models import User, Tenant, Membership

db = SessionLocal()
try:
    # Count users
    user_count = db.query(User).count()
    print(f"Total users: {user_count}")

    # Find admin@test.com
    admin = db.query(User).filter(User.email == "admin@test.com").first()
    if admin:
        print(f"Admin user found: {admin.user_id}")
        print(f"  Email: {admin.email}")
        print(f"  Active: {admin.is_active}")
        print(f"  Deleted: {admin.deleted_at}")

        # Check memberships
        memberships = db.query(Membership).filter(Membership.user_id == admin.user_id).all()
        print(f"  Memberships: {len(memberships)}")
        for m in memberships:
            print(f"    - Tenant: {m.tenant_id}, Role: {m.role}, Active: {m.is_active}")
    else:
        print("Admin user NOT FOUND")
finally:
    db.close()
