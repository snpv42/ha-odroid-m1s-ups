#!/usr/bin/env python3
"""Render the M1S virtual device plus user-supplied standard NUT devices."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def line(value: object, field: str) -> str:
    text = str(value)
    if "\n" in text or "\r" in text:
        raise ValueError(f"{field} must not contain a newline")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--data-file", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    m1s_name = line(config["ups_name"], "ups_name")
    if not NAME.fullmatch(m1s_name):
        raise SystemExit("ups_name contains unsupported characters")

    blocks = [
        f"[{m1s_name}]",
        "    driver = dummy-ups",
        f"    port = {line(args.data_file, 'data-file')}",
        '    desc = "Hardkernel UPS Kit for ODROID-M1S"',
        "    pollinterval = 1",
    ]
    names = {m1s_name}
    for device in config.get("additional_devices", []):
        name = line(device["name"], "additional_devices.name")
        if not NAME.fullmatch(name) or name in names:
            raise SystemExit(f"invalid or duplicate UPS name: {name!r}")
        names.add(name)
        blocks.extend(("", f"[{name}]", f"    driver = {line(device['driver'], 'driver')}",
                       f"    port = {line(device['port'], 'port')}"))
        for option in device.get("config", []):
            blocks.append(f"    {line(option, 'config option')}")

    args.output.write_text("\n".join(blocks) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
