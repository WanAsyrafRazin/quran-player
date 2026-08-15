# TASK — HomeBridge + Tuya-local: Siri control for SMATRUL garage switch

Build this on the PC (Windows, home WiFi). Self-contained task — user approved.

## Goal
Install HomeBridge on this PC with the Tuya local-protocol plugin so the
SMATRUL WiFi garage switch (Tuya-based) appears in Apple Home, controllable
by Siri ("Hey Siri, open the gate").

Context: the cloud API only exposes the switch's master channel (buttons 1&2
are hidden from the cloud), so the LOCAL protocol is the way to reach all
channels. This PC is on the same home WiFi as the switch — required.

## Steps

1. **Install Node.js** if not present (HomeBridge needs Node 18+):
   - `node --version` first; if missing or < 18, install LTS from
     https://nodejs.org (winget: `winget install OpenJS.NodeJS.LTS`)

2. **Install HomeBridge globally**:
   ```
   npm install -g homebridge homebridge-config-ui-x
   ```
   (config-ui-x gives a web dashboard at http://localhost:8581 — optional but
   useful. Admin user set via `homebridge-config-ui-x` first-run wizard.)

3. **Install the Tuya local plugin**:
   ```
   npm install -g homebridge-tuya-local
   ```

4. **Find the switch's device credentials** — the plugin needs:
   - Device IP (find in router admin or Tuya app → device info, or scan:
     `nmap -sn 192.168.1.0/24` or check the Tuya app's "device info")
   - Device ID (tuya ID, 20-char hex-ish string)
   - Local key (16-char hex string)
   - Version (3.3 or 3.4/3.5)

   How to get them:
   - **Easiest**: if a `tuyalocal` / `tuyapi` / `tuya-local` helper or the
     `homebridge-tuya-local` docs' "find device credentials" guide is
     reachable, follow it. The local key can often be extracted from the
     Tuya app's captured traffic (see note below) OR via the plugin's
     bundled discovery.
   - **Fallback**: ask the user if they know the Tuya developer-cloud
     credentials; alternatively check the router's DHCP table for the
     switch's IP and try `tuya-cli` (`npm i -g tuya-cli`, `tuya-cli wizard`
     — it extracts the local key from the cloud API when given the app's
     API credentials).
   - If the local key is unobtainable, report that clearly and stop — do
     NOT guess keys.

5. **Configure the accessory** in `~/.homebridge/config.json`:
   ```json
   {
     "bridge": { "name": "HomeBridge", "username": "CC:22:3D:E3:CE:30", "port": 51826, "pin": "031-45-154" },
     "accessories": [
       {
         "accessory": "TuyaLocal",
         "name": "Garage Gate",
         "device_id": "<DEVICE_ID>",
         "local_key": "<LOCAL_KEY>",
         "ip": "<DEVICE_IP>",
         "protocol_version": "3.3",
         "type": "switch",
         "pollingInterval": 3000
       }
     ]
   }
   ```
   If the SMATRUL exposes two channels, add a second accessory or use the
   plugin's multi-channel config (check plugin README). Name them e.g.
   "Gate Channel 1" / "Gate Channel 2".

6. **Run HomeBridge** (background/daemon):
   - Test first: `homebridge` in a terminal — watch the log for
     "TuyaLocal" accessory appearing and successful pairing (no auth errors).
   - Then set it up to auto-start: on Windows, `homebridge-config-ui-x`
     can install it as a Windows service, or use NSSM
     (`nssm install homebridge "C:\Program Files\nodejs\node.exe" "<npm global homebridge path>"`).

7. **Pair with Apple Home**: open the Home app on the user's iPhone/iPad →
   Add Accessory → scan the HomeBridge QR code (shown in config-ui-x) or
   enter the PIN (default 031-45-154). The "Garage Gate" switch(es) should
   appear.

8. **Verify with Siri**: ask the user to say "Hey Siri, turn on Garage Gate"
   and confirm the gate actually switches. If nothing happens, check:
   - HomeBridge log for auth/timeout errors (wrong key/IP/version)
   - Try `protocol_version` 3.4 or 3.5 if 3.3 fails (SMATRUL devices vary)
   - `pollingInterval` smaller (1000) if status lags

9. **Report back**:
   - Node version, HomeBridge version, plugin version
   - The device credentials found (mask the local_key — show first 4 chars)
   - Whether both channels appeared in Home, and Siri test result
   - Any error logs that blocked progress

## Notes
- Windows firewall: allow node.exe on private networks (HomeKit + Tuya LAN).
- HomeBridge must stay running while the user wants Siri control — if the PC
  sleeps, set Windows power plan to "Never sleep" (or at least disable sleep
  while plugged in) and tell the user about this trade-off.
- Do NOT publish the local_key or device_id anywhere public.
