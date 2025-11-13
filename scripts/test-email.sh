#!/bin/bash
# Send test email to the local SMTP server

set -e

echo "======================================"
echo "Send Test Email"
echo "======================================"
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Create Python script to send email
python3 << 'EOF'
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Email configuration
SMTP_HOST = "localhost"
SMTP_PORT = 2525
FROM_EMAIL = "sender@example.com"
TO_EMAIL = "test@emails.listfig.com"

# Create email
msg = MIMEMultipart("alternative")
msg["Subject"] = f"Test Email - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
msg["From"] = FROM_EMAIL
msg["To"] = TO_EMAIL
msg["Message-ID"] = f"<test-{datetime.now().timestamp()}@example.com>"

# Plain text version
text = """
Hello!

This is a test email sent to the Listfig email processing system.

This email should be:
1. Received by Haraka SMTP server
2. Forwarded to FastAPI webhook
3. Processed by Temporal workflow
4. Analyzed by OpenAI for summary and categorization
5. Stored in PostgreSQL database

You can check the processing status in:
- Temporal UI: http://localhost:8080
- API: http://localhost:8000/emails

Best regards,
Test Script
"""

# HTML version
html = """
<html>
  <body>
    <h2>Test Email</h2>
    <p>This is a test email sent to the Listfig email processing system.</p>

    <p>This email should be:</p>
    <ol>
      <li>Received by Haraka SMTP server</li>
      <li>Forwarded to FastAPI webhook</li>
      <li>Processed by Temporal workflow</li>
      <li>Analyzed by OpenAI for summary and categorization</li>
      <li>Stored in PostgreSQL database</li>
    </ol>

    <p>You can check the processing status in:</p>
    <ul>
      <li>Temporal UI: <a href="http://localhost:8080">http://localhost:8080</a></li>
      <li>API: <a href="http://localhost:8000/emails">http://localhost:8000/emails</a></li>
    </ul>

    <p>Best regards,<br>Test Script</p>
  </body>
</html>
"""

# Attach parts
part1 = MIMEText(text, "plain")
part2 = MIMEText(html, "html")
msg.attach(part1)
msg.attach(part2)

# Send email
try:
    print(f"Connecting to SMTP server at {SMTP_HOST}:{SMTP_PORT}...")
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        print(f"Sending email from {FROM_EMAIL} to {TO_EMAIL}...")
        server.send_message(msg)
        print("✓ Email sent successfully!")
        print("")
        print(f"Message ID: {msg['Message-ID']}")
        print(f"Subject: {msg['Subject']}")
        print("")
        print("Check processing status:")
        print("  - Temporal UI: http://localhost:8080")
        print("  - View emails: http://localhost:8000/emails")
        print("  - View logs: cd infrastructure/docker && docker-compose logs -f")
        print("")
except Exception as e:
    print(f"✗ Failed to send email: {e}")
    print("")
    print("Make sure the services are running:")
    print("  ./scripts/setup-dev.sh")
    exit(1)
EOF

echo ""
