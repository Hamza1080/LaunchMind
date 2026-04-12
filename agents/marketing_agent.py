import json
import re
import os
import requests
from llm import call_llm
from message_bus import send_message, get_messages, make_message
import smtplib
from email.mime.text import MIMEText

AGENT_NAME = "marketing"

EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SLACK_BOT_TOKEN   = os.getenv("SLACK_BOT_TOKEN")
SLACK_CHANNEL     = os.getenv("SLACK_CHANNEL", "#launches")


def run(pr_url: str = None):
    print("\n[MARKETING AGENT] Starting...")

    messages = get_messages(AGENT_NAME)
    spec_msg = next((m for m in messages if m["message_type"] == "result"), None)
    if not spec_msg:
        print("[MARKETING AGENT] No product spec found.")
        return None

    spec = spec_msg["payload"]["product_spec"]

    # Pick up PR URL forwarded by CEO if not passed directly
    if not pr_url:
        for m in messages:
            if m.get("from_agent") == "ceo" and "pr_url" in m.get("payload", {}):
                pr_url = m["payload"]["pr_url"]
                break

    print(f"[MARKETING AGENT] Generating copy for: {spec['value_proposition']}")
    copy = _generate_copy(spec)

    _send_email(copy, spec)
    _post_slack(copy, spec, pr_url or "https://github.com/placeholder/pr/1")

    send_message(make_message(
        from_agent=AGENT_NAME,
        to_agent="ceo",
        message_type="result",
        payload=copy,
    ))

    print("[MARKETING AGENT] Done.")
    return copy


# ── Copy generation ───────────────────────────────────────────────────────────

def _generate_copy(spec: dict) -> dict:
    features_text = ", ".join(f["name"] for f in spec["features"][:3])

    prompt = f"""You are a growth marketer for a tech startup.

Product: {spec['value_proposition']}
Top features: {features_text}

Generate marketing copy as a JSON object with EXACTLY this structure:
{{
  "tagline": "under 10 words, punchy and memorable",
  "description": "2 sentences for a landing page",
  "email_subject": "compelling cold outreach subject line",
  "email_body": "3-paragraph cold outreach email to a potential early user. Include a clear call to action.",
  "twitter": "tweet under 280 chars with 2 hashtags",
  "linkedin": "professional LinkedIn post 3-4 sentences",
  "instagram": "casual Instagram caption with emojis and hashtags"
}}

IMPORTANT: The email_body must use \\n for line breaks — no raw newlines inside the JSON string.
Return ONLY the JSON. No markdown. No explanation."""

    raw = call_llm(prompt)
    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    # Remove control characters that break JSON (raw newlines inside strings)
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', raw)   # strip non-printable
    raw = re.sub(r'(?<!\\)\n', ' ', raw)                        # collapse bare newlines

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            chunk = match.group()
            chunk = re.sub(r'(?<!\\)\n', ' ', chunk)
            return json.loads(chunk)
        raise ValueError(f"[MARKETING AGENT] Could not parse copy JSON:\n{raw}")


# ── gmail email ────────────────────────────────────────────────────────────

def _send_email(copy: dict, spec: dict):
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("[MARKETING AGENT] Gmail credentials missing — skipping email.")
        return

    body_text = copy["email_body"].replace("\\n", "\n")

    msg = MIMEText(body_text)
    msg["Subject"] = copy["email_subject"]
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = EMAIL_ADDRESS  # send to yourself

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)

        print(f"[MARKETING AGENT] Email sent ✓ Subject: {copy['email_subject']}")

    except Exception as e:
        print(f"[MARKETING AGENT] Gmail send failed: {e}")

# ── Slack Block Kit ───────────────────────────────────────────────────────────

def _post_slack(copy: dict, spec: dict, pr_url: str):
    if not SLACK_BOT_TOKEN:
        print("[MARKETING AGENT] SLACK_BOT_TOKEN missing — skipping Slack post.")
        return

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"LaunchMind: {copy['tagline']}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{spec['value_proposition']}*\n{copy['description']}",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*GitHub PR:*\n<{pr_url}|View PR →>"},
                {"type": "mrkdwn", "text": f"*Email:*\nSent via Gmail"},
                {"type": "mrkdwn", "text": f"*Twitter:*\n{copy['twitter'][:120]}…"},
                {"type": "mrkdwn", "text": "*Agents:* CEO · Product · Engineer · Marketing · QA"},
            ],
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": "_Built autonomously by LaunchMind agents_"},
            ],
        },
    ]

    try:
        r = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type":  "application/json",
            },
            json={"channel": SLACK_CHANNEL, "blocks": blocks},
        )
        data = r.json()
        if data.get("ok"):
            print(f"[MARKETING AGENT] Slack Block Kit posted ✓  channel: {SLACK_CHANNEL}")
        else:
            print(f"[MARKETING AGENT] Slack error: {data.get('error')}")
    except Exception as e:
        print(f"[MARKETING AGENT] Slack post failed: {e}")