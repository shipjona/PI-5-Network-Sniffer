from __future__ import annotations

from grizzl.database import initialize_database, sync_chargers
from grizzl.config import CHARGERS
from grizzl.logging_config import configure_logging
from grizzl.services.polling import run_forever


def main() -> int:
    configure_logging()
    initialize_database()
    sync_chargers(CHARGERS)
    run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
