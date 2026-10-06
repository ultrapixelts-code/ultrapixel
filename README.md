# UltraPixel website backend

Stores website requests, emails them to info@ultrapixel.it, counts first-party statistics and offers an admin page with status tracking and CSV/XLSX export.

Render web service: build `pip install -r requirements.txt`, start `gunicorn app:app`, health check `/healthz`.
Environment variables: `DATABASE_URL`, `ALLOWED_ORIGINS`, `ADMIN_USER`, `ADMIN_PASSWORD`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`, `NOTIFY_TO`.
Then in the site's `content/en.json` set `site.formEndpoint` to `https://<service>/api/lead` and `site.analyticsEndpoint` to `https://<service>/api/event`, and rebuild.

Tables `web_leads` and `web_events` are created on start. No IP address is stored.
