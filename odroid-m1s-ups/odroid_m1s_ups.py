#!/usr/bin/env python3
"""Translate the M1S UPS serial event stream into a live NUT dummy-ups file.

Hardkernel documents the interface as a serial endpoint that emits a low-battery
warning, not as a USB HID UPS protocol.  The regexes are options intentionally:
they make this bridge usable with firmware revisions whose text differs.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import signal
import sys
import time
from pathlib import Path

import serial


RUNNING = True


def stop(*_args: object) -> None:
    global RUNNING
    RUNNING = False


def nut_value(value: object) -> str:
    """Return a dummy-ups-safe value (quote strings containing whitespace)."""
    text = str(value).replace('"', "'")
    return f'"{text}"' if any(c.isspace() for c in text) else text


def write_state(path: Path, values: dict[str, object]) -> None:
    """Atomically update the definition file; dummy-ups notices its mtime."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(f"{key}: {nut_value(value)}" for key, value in values.items()) + "\n")
    os.replace(tmp, path)


def compile_pattern(config: dict[str, object], name: str) -> re.Pattern[str]:
    try:
        return re.compile(str(config[name]))
    except re.error as error:
        raise SystemExit(f"Invalid {name}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--state-file", required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())

    patterns = {name: compile_pattern(config, name) for name in (
        "on_battery_regex", "online_regex", "low_battery_regex",
        "battery_charge_regex", "battery_voltage_regex",
    )}
    values: dict[str, object] = {
        "device.mfr": "Hardkernel",
        "device.model": "UPS Kit for ODROID-M1S",
        "device.type": "ups",
        "ups.status": "OL",
        "driver.version.internal": "odroid-m1s-serial-bridge-0.2.0",
    }
    write_state(args.state_file, values)
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    raw_log = Path("/data/odroid-m1s-ups.raw.log") if config.get("raw_log") else None
    while RUNNING:
        try:
            with serial.Serial(str(config["serial_port"]), int(config["baudrate"]), timeout=1) as port:
                logging.warning("connected to %s at %s baud", port.name, port.baudrate)
                while RUNNING:
                    raw = port.readline()
                    if not raw:
                        continue
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    logging.info("UPS serial: %s", line)
                    if raw_log:
                        with raw_log.open("a", encoding="utf-8") as log:
                            log.write(f"{time.strftime('%FT%TZ', time.gmtime())} {line}\n")

                    changed = False
                    if patterns["low_battery_regex"].search(line):
                        values["ups.status"] = "OB LB"
                        changed = True
                    elif patterns["on_battery_regex"].search(line):
                        values["ups.status"] = "OB"
                        changed = True
                    elif patterns["online_regex"].search(line):
                        values["ups.status"] = "OL"
                        changed = True

                    for key, variable in (("battery_charge_regex", "battery.charge"),
                                          ("battery_voltage_regex", "battery.voltage")):
                        match = patterns[key].search(line)
                        if match:
                            values[variable] = match.group(1)
                            changed = True
                    if changed:
                        write_state(args.state_file, values)
        except (serial.SerialException, OSError) as error:
            logging.error("serial connection failed: %s; retrying in 5 seconds", error)
            time.sleep(5)
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    sys.exit(main())
