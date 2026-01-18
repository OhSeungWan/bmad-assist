# Notifications Module

Real-time webhook notifications for bmad-assist workflow events via Telegram and Discord.

## Quick Start

### 1. Configure Environment Variables

```bash
# Telegram
export TELEGRAM_BOT_TOKEN="your-bot-token"
export TELEGRAM_CHAT_ID="your-chat-id"

# Discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

### 2. Add to bmad-assist.yaml

```yaml
notifications:
  enabled: true
  providers:
    - type: telegram
      bot_token: ${TELEGRAM_BOT_TOKEN}
      chat_id: ${TELEGRAM_CHAT_ID}
    - type: discord
      webhook_url: ${DISCORD_WEBHOOK_URL}
  events:
    - story_started
    - story_completed
    - phase_completed
    - error_occurred
```

---

## Telegram Setup

### Step 1: Create a Bot with BotFather

1. Open Telegram and search for `@BotFather`
2. Send `/newbot`
3. Follow prompts to name your bot
4. Copy the **bot token** (looks like `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)

### Step 2: Get Your Chat ID

**Option A: Personal Chat**
1. Start a chat with your new bot (search for it by name)
2. Send any message to the bot
3. Open: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Find `"chat":{"id":123456789}` - that's your chat_id

**Option B: Group Chat**
1. Add your bot to the group
2. Send a message in the group
3. Use the getUpdates URL above
4. Group chat IDs are negative (e.g., `-987654321`)

**Option C: Channel**
1. Add bot as admin to your channel
2. Forward a channel message to `@userinfobot`
3. Use the channel ID (starts with `-100`)

### Step 3: Test

```bash
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "'${TELEGRAM_CHAT_ID}'", "text": "Test notification!"}'
```

---

## Discord Setup

### Step 1: Create a Webhook

1. Open Discord and go to your server
2. Right-click the channel → **Edit Channel**
3. Go to **Integrations** → **Webhooks**
4. Click **New Webhook**
5. Name it (e.g., "bmad-assist")
6. Click **Copy Webhook URL**

The URL looks like: `https://discord.com/api/webhooks/123456789/abcdefghijk...`

### Step 2: Test

```bash
curl -X POST "${DISCORD_WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Test notification!"}'
```

---

## Configuration Reference

### Provider Options

**Telegram:**
```yaml
- type: telegram
  bot_token: ${TELEGRAM_BOT_TOKEN}  # Required
  chat_id: ${TELEGRAM_CHAT_ID}      # Required
```

**Discord:**
```yaml
- type: discord
  webhook_url: ${DISCORD_WEBHOOK_URL}  # Required
```

### Available Events

| Event | Priority | When Triggered |
|-------|----------|----------------|
| `story_started` | Normal | New story begins |
| `story_completed` | Normal | Story finishes successfully |
| `phase_completed` | Normal | Workflow phase completes |
| `error_occurred` | HIGH | Phase fails with error |
| `anomaly_detected` | HIGH | Guardian detects anomaly (Phase 2) |
| `queue_blocked` | HIGH | Workflow queue blocked (Phase 2) |

### Minimal Config (Single Provider)

```yaml
notifications:
  enabled: true
  providers:
    - type: telegram
      bot_token: ${TELEGRAM_BOT_TOKEN}
      chat_id: ${TELEGRAM_CHAT_ID}
  events:
    - error_occurred  # Only get notified on errors
```

### Full Config (Both Providers)

```yaml
notifications:
  enabled: true
  providers:
    - type: telegram
      bot_token: ${TELEGRAM_BOT_TOKEN}
      chat_id: ${TELEGRAM_CHAT_ID}
    - type: discord
      webhook_url: ${DISCORD_WEBHOOK_URL}
  events:
    - story_started
    - story_completed
    - phase_completed
    - error_occurred
```

---

## Troubleshooting

### Telegram: "chat not found"
- Ensure you've sent at least one message to the bot first
- Verify chat_id is correct (use getUpdates to check)
- For groups: make sure bot is a member

### Telegram: "Unauthorized"
- Bot token is invalid or expired
- Create a new bot with BotFather

### Discord: "Unknown Webhook"
- Webhook was deleted from Discord
- Create a new webhook

### No notifications received
1. Check `notifications.enabled: true`
2. Verify event is in `events` list
3. Check environment variables are set: `echo $TELEGRAM_BOT_TOKEN`
4. Look for errors in bmad-assist logs

### Rate Limiting
- Telegram: 30 messages/second (rarely hit)
- Discord: 30 requests/60 seconds per webhook
- Both providers have built-in retry with backoff

---

## Security Notes

- **Never commit tokens** to git - always use environment variables
- Bot tokens and webhook URLs are secrets - treat them like passwords
- Consider using a dedicated bot/webhook for bmad-assist
- Webhook URLs contain both ID and token - keep them private

---

## Architecture

```
notifications/
├── __init__.py       # Public API exports
├── base.py           # NotificationProvider ABC
├── events.py         # EventType enum + payload models
├── telegram.py       # TelegramProvider
├── discord.py        # DiscordProvider
├── config.py         # NotificationConfig Pydantic model
└── dispatcher.py     # EventDispatcher + global accessors
```

All providers implement fire-and-forget pattern - failures are logged but never block the main workflow.
