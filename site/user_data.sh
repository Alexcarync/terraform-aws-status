#!/bin/bash
set -e
apt-get update
apt-get install -y nginx git
rm -rf /var/www/html/*
git clone --depth 1 ${repo_url} /tmp/site
cp -r /tmp/site/site/* /var/www/html/
systemctl enable --now nginx