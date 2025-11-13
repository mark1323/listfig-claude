# Haraka Email Receiver

SMTP server for receiving emails across multiple domains and forwarding them to the email-processor service.

## Configuration

### Environment Variables

- `EMAIL_PROCESSOR_URL`: URL of the email processor API (default: `http://email-processor:8000`)
- `API_KEY`: API key for authenticating with email processor
- `EMAIL_DOMAINS`: Comma-separated list of domains to accept emails for

### Email Domains

Add domains to `config/host_list` (one per line):

```
emails.listfig.com
mail.listfig.com
inbox.listfig.com
```

Or set via environment variable:
```bash
EMAIL_DOMAINS=emails.listfig.com,mail.listfig.com
```

## Development

### Local Testing

Send a test email:
```bash
# Using swaks
swaks --to test@emails.listfig.com \
      --from sender@example.com \
      --server localhost:2525 \
      --body "Test email body"

# Using Python
python scripts/test-email.py
```

### Logs

View Haraka logs:
```bash
docker-compose logs -f haraka
```

## Production Notes

- Port 25 requires root privileges; use port 587 or configure capabilities
- Set up SPF/DKIM/DMARC records for each domain
- Configure TLS certificates in `smtp.ini`
- Use proper API key (not dev-secret-key)
