#!/bin/bash
set -euxo pipefail

apt-get update
apt-get install -y nginx git

# --- site content ---
rm -rf /var/www/html/*
git clone --depth 1 ${repo_url} /tmp/repo
cp -r /tmp/repo/site/* /var/www/html/

# --- checker ---
install -d /opt/statuspage /var/lib/statuspage
install -m 755 /tmp/repo/check.py     /opt/statuspage/check.py
install -m 644 /tmp/repo/targets.json /opt/statuspage/targets.json

# First run so the page has data before anyone loads it
/opt/statuspage/check.py || true

# --- schedule ---
cat > /etc/cron.d/statuspage <<'CRON'
*/5 * * * * root /opt/statuspage/check.py >> /var/log/statuspage.log 2>&1
CRON
chmod 644 /etc/cron.d/statuspage

systemctl enable --now nginx
systemctl restart cron