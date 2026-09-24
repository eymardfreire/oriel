"""Run the aggregation service on the address in config.toml."""

from __future__ import annotations

import sys

import uvicorn

from oriel_server.config import load_config
from oriel_server.main import create_app


def main() -> None:
    if sys.version_info < (3, 12):
        found = sys.version.split()[0]
        raise SystemExit(f"Oriel server requires Python 3.12 or newer (found {found})")
    config = load_config()
    uvicorn.run(create_app(config), host=config.bind_host, port=config.bind_port)


if __name__ == "__main__":
    main()
