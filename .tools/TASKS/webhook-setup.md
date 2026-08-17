# TASK — Enable Hermes webhook platform on this PC (direct agent-to-agent link)

Goal: let the VPS Hermes POST tasks to this PC Hermes directly (Option B —
webhook over Tailscale). This PC Hermes becomes reachable via HTTP; the VPS
will trigger full agent runs here and results get delivered to Asyraf's chat.

## Why
We already have Tailscale (PC = 100.113.239.48, VPS = 100.104.153.112).
The GitHub task channel works but is indirect; a webhook gives real-time
two-way agent communication using Hermes's first-class webhook platform.

## Steps (on this PC)

1. **Check webhook platform status:**
   ```
   hermes webhook list
   ```
   If it says "Webhook platform is not enabled", continue to step 2.
   If already enabled, skip to step 4.

2. **Enable the webhook platform.** Add to `~/.hermes/config.yaml` (or via
   `hermes gateway setup` wizard):
   ```yaml
   platforms:
     webhook:
       enabled: true
       extra:
         port: 8644
         secret: "<generate-a-long-random-string>"
   ```
   Generate the secret yourself (e.g. `openssl rand -hex 32` or a long
   random string). Keep it in this config only.

3. **Restart the gateway** so the webhook server starts:
   ```
   hermes gateway restart
   ```
   (or `hermes gateway run` if not running as a service).

4. **Verify it's listening** (on this PC):
   ```
   curl http://localhost:8644/health
   ```
   Expect: `{"status": "ok"}`.

5. **Create a subscription for VPS-triggered tasks:**
   ```
   hermes webhook subscribe vps-tasks ^
     --prompt "Task from VPS Hermes: {payload.task}" ^
     --events "task" ^
     --description "Direct tasks from the VPS Hermes agent" ^
     --deliver telegram ^
     --deliver-chat-id "147135402"
   ```
   (PowerShell uses backtick ` instead of ^ for line continuation; or put
   it on one line.)
   Note the returned **webhook URL** and **HMAC secret**.

6. **IMPORTANT — share the credentials with the VPS Hermes via the PRIVATE
   channel only:** create a file in the private repo:
   ```
   cd C:/Users/A/Desktop/Github-Project/server-tools   (or wherever cloned)
   ```
   Write `handover/webhook-endpoint.md` with:
   - The webhook URL (should be the Tailscale-reachable URL —
     http://100.113.239.48:8644/webhook/<name> or similar)
   - The HMAC secret
   - The event name ("task")
   Then commit + push to `master` (the private repo). **Do NOT put this in
   quran-player (.tools/TASKS/) — that repo is PUBLIC.**

7. **Test locally:**
   ```
   hermes webhook test vps-tasks --payload "{\"task\": \"test ping from PC side\"}"
   ```
   Expect: agent runs, result delivered to Telegram chat 147135402.

## Report back
- Webhook platform enabled? Listening on 8644?
- Subscription name + event
- URL + secret saved to server-tools handover/webhook-endpoint.md (pushed)
- Local test result
