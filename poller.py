from __future__ import annotations

from grizzl.logging_config import configure_logging
from grizzl.services.polling import run_forever


def main() -> None:
    configure_logging()
    run_forever()


if __name__ == "__main__":
    main()
