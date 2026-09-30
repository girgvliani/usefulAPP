"""Admin commands for the home server. Run from the backend folder:

    python manage.py create-user you@example.com
    python manage.py new-device you@example.com "Galaxy S23"
    python manage.py list-devices you@example.com
    python manage.py revoke-device you@example.com 3
"""

import argparse
import getpass
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models import DeviceToken, User
from app.security import hash_password, new_device_token, verify_password
from app.services import rpg_logic


def fail(message):
    print(f"❌ {message}")
    sys.exit(1)


def login(db, email):
    """Asks for the password, the same check the login endpoint does."""
    user = db.scalar(select(User).where(User.email == email))
    if not user or not verify_password(getpass.getpass("Password: "), user.hashed_password):
        fail("Wrong email or password")
    return user


def create_user(db, args):
    if db.scalar(select(User).where(User.email == args.email)):
        fail("That email is already registered")
    password = getpass.getpass("New password (8+ characters): ")
    if len(password) < 8:
        fail("Password must be at least 8 characters")
    if getpass.getpass("Repeat it: ") != password:
        fail("Passwords don't match")
    user = User(email=args.email, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    rpg_logic.seed_new_user(db, user)
    print(f"✅ Created {user.email}")


def new_device(db, args):
    user = login(db, args.email)
    token, token_hash = new_device_token()
    db.add(DeviceToken(user_id=user.id, name=args.name, token_hash=token_hash))
    db.commit()
    print(f"✅ Device '{args.name}' created. Copy this token now, it won't be shown again:\n\n    {token}\n")


def list_devices(db, args):
    user = login(db, args.email)
    devices = db.scalars(select(DeviceToken).where(DeviceToken.user_id == user.id).order_by(DeviceToken.id))
    for d in devices:
        print(f"  [{d.id}] {d.name:20} created {d.created_at:%Y-%m-%d}  last used {d.last_used_at or 'never'}")


def revoke_device(db, args):
    user = login(db, args.email)
    device = db.scalar(select(DeviceToken).where(DeviceToken.user_id == user.id, DeviceToken.id == args.id))
    if not device:
        fail("No such device")
    db.delete(device)
    db.commit()
    print(f"✅ Revoked '{device.name}'")


def main():
    parser = argparse.ArgumentParser(description="Life RPG server admin")
    commands = parser.add_subparsers(dest="command", required=True)

    p = commands.add_parser("create-user", help="register an account")
    p.add_argument("email")
    p.set_defaults(run=create_user)

    p = commands.add_parser("new-device", help="create a token for a phone or other device")
    p.add_argument("email")
    p.add_argument("name")
    p.set_defaults(run=new_device)

    p = commands.add_parser("list-devices", help="show device tokens")
    p.add_argument("email")
    p.set_defaults(run=list_devices)

    p = commands.add_parser("revoke-device", help="cancel a device token")
    p.add_argument("email")
    p.add_argument("id", type=int)
    p.set_defaults(run=revoke_device)

    args = parser.parse_args()
    with SessionLocal() as db:
        args.run(db, args)


if __name__ == "__main__":
    main()
