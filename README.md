# ODROID M1S UPS NUT bridge

This is a Home Assistant add-on that exposes the Hardkernel **UPS Kit for
ODROID-M1S** as a real NUT server. It is deliberately not configured as
`usbhid-ups`: the M1S UPS is documented as a serial (`ttyACM`) device that
sends a low-battery warning, rather than a USB HID Power Device.

The add-on runs a small serial bridge and NUT's built-in `dummy-ups` driver.
The bridge turns serial events into standard NUT state: `OL`, `OB`, and
`OB LB`. Home Assistant can then use its ordinary NUT integration.

## Install

1. Copy this `odroid-m1s-ups-nut` directory into a Git repository you control.
   The Home Assistant add-on store only accepts repositories; `repository.yaml`
   is at the repository root.
2. In Home Assistant, add that repository under **Settings → Add-ons → Add-on
   store → ⋮ → Repositories**, then install **ODROID M1S UPS (NUT)**.
3. Set `serial_port` to the endpoint shown by the host. Start with
   `/dev/ttyACM0`; if it differs, inspect the host's device list. The add-on
   requests UART access.
4. Replace the default password, start the add-on, and add Home Assistant's
   built-in NUT integration using host `127.0.0.1`, port `3493`, the configured
   username/password, and UPS name `odroid_m1s_ups`.

Do not run this alongside the community NUT app for the same UPS: only one
process may open the serial device, and each is a NUT server. This add-on is a
drop-in replacement for that app for this UPS.

## Add an APC UPS (or other NUT-supported device)

Use `additional_devices` to configure ordinary NUT devices in the same server.
For a USB-connected APC, add:

```yaml
additional_devices:
  - name: apc
    driver: usbhid-ups
    port: auto
    config: []
```

If the APC supplies power to the M1S UPS, use `odroid_m1s_ups` as the shutdown
signal in Home Assistant: it is the final device powering the Odroid after the
APC output is unavailable. The APC is still fully monitored, and Home Assistant
will discover both UPS names from this one NUT server. This add-on does not run
`upsmon` or shut down the host itself; create a Home Assistant automation that
reacts to `odroid_m1s_ups` reporting `OB LB` when you are ready to enable a host
shutdown action.

## Verify and calibrate the serial protocol

Hardkernel’s public documentation confirms the serial transport and low-battery
warning but does not publish its message grammar. This driver therefore logs
every received line and makes patterns configurable. Enable `raw_log: true`,
remove mains power briefly, restore it, and inspect the add-on log and
`/data/odroid-m1s-ups.raw.log`.

The default regular expressions recognize common phrases. If your firmware
emits a different token, set the matching `*_regex` option. For example, if the
log contains `PWRFAIL`, use `on_battery_regex: '^PWRFAIL$'`. Do not invent an
event format: calibrate from the device's actual log before relying on automatic
shutdown behavior.

Useful NUT checks from a machine with NUT clients installed:

```sh
upsc odroid_m1s_ups@HOME_ASSISTANT_HOST
```

Expected initial output includes `ups.status: OL`. After the UPS emits its low
battery warning it must show `ups.status: OB LB`.

## Scope

The device advertises a low-battery warning, so this driver safely exposes the
power state needed for NUT events. Battery percentage and voltage appear only
when the firmware actually includes them in serial messages; they are never
fabricated. The UPS itself powers the M1S back on after mains returns.
