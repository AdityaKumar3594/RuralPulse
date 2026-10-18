"""Administrator command line: `python -m app.admin.cli create-user --role admin ...`.

The first administrator has to be created here; everyone else can be created through the admin
API. The PIN is read from a hidden prompt unless --pin is given (avoid --pin on shared shells).
"""

import argparse
import getpass
import sys

from app.core.config import get_settings
from app.core.db import make_engine, make_session_factory
from app.modules.identity import service
from app.modules.identity.models import Role


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="admin")
    sub = parser.add_subparsers(dest="command", required=True)
    create = sub.add_parser("create-user", help="create an admin, facilitator or partner account")
    create.add_argument("--role", choices=[r.value for r in service.STAFF_ROLES], required=True)
    create.add_argument("--phone", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--pin", help="6-12 digits; prompted (hidden) if omitted")
    args = parser.parse_args(argv)

    pin = args.pin or getpass.getpass("PIN (6-12 digits): ")
    settings = get_settings()
    with make_session_factory(make_engine(settings))() as db:
        try:
            user = service.create_staff_user(db, Role(args.role), args.phone, pin, args.name, None)
        except service.WeakStaffPin:
            print("PIN must be 6 to 12 digits.", file=sys.stderr)
            return 1
        except service.PhoneAlreadyRegistered:
            print("That phone number already has an account.", file=sys.stderr)
            return 1
    print(f"created {args.role} {user.id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
