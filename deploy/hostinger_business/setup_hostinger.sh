#!/usr/bin/env bash
# AstroNaradMuni v1.4.0 — One-Command Installer for Hostinger Business Web Hosting (SSH)
# Run this inside your Hostinger SSH terminal after cloning or uploading ~/Astrobrain:
#   bash ~/Astrobrain/deploy/hostinger_business/setup_hostinger.sh <DOMAIN_NAME> <MYSQL_DB> <MYSQL_USER> <MYSQL_PASS> [ADMIN_KEY]

set -euo pipefail

DOMAIN="${1:-}"
DB_NAME="${2:-}"
DB_USER="${3:-}"
DB_PASS="${4:-}"
ADMIN_KEY="${5:-}"

if [[ -z "$DOMAIN" || -z "$DB_NAME" || -z "$DB_USER" || -z "$DB_PASS" ]]; then
  echo "Usage: bash setup_hostinger.sh <yourdomain.com> <uXXX_astrodb> <uXXX_astro> <db_password> [admin_secret_key]"
  exit 1
fi

APP_DIR="$HOME/Astrobrain"
VENV_DIR="$HOME/astro_venv"
PUBLIC_HTML="$HOME/domains/$DOMAIN/public_html"

if [[ ! -d "$PUBLIC_HTML" ]]; then
  echo "Error: Could not find $PUBLIC_HTML. Check your domain folder under ~/domains/"
  exit 1
fi

echo "==> [1/4] Creating Python virtual environment at $VENV_DIR..."
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install "$APP_DIR" pymysql

echo "==> [2/4] Copying frontend assets (index.html + static/) to $PUBLIC_HTML..."
cp "$APP_DIR/src/aipandit/web/static/index.html" "$PUBLIC_HTML/index.html"
mkdir -p "$PUBLIC_HTML/static"
cp -R "$APP_DIR/src/aipandit/web/static/"* "$PUBLIC_HTML/static/"

echo "==> [3/4] Installing LiteSpeed .htaccess and configuring api_gateway.php..."
cp "$APP_DIR/deploy/hostinger_business/.htaccess" "$PUBLIC_HTML/.htaccess"
sed \
  -e "s|u123456789_astrodb|${DB_NAME}|g" \
  -e "s|u123456789_astro|${DB_USER}|g" \
  -e "s|REPLACE_WITH_DB_PASS|${DB_PASS}|g" \
  -e "s|\$ADMIN_KEY      = getenv('ASTROMUNI_ADMIN_KEY') ?: '';|\$ADMIN_KEY      = getenv('ASTROMUNI_ADMIN_KEY') ?: '${ADMIN_KEY}';|g" \
  "$APP_DIR/deploy/hostinger_business/api_gateway.php" > "$PUBLIC_HTML/api_gateway.php"

echo "==> [4/4] Initializing MySQL tables in $DB_NAME..."
MYSQL_HOST="127.0.0.1" MYSQL_PORT="3306" MYSQL_DATABASE="$DB_NAME" MYSQL_USER="$DB_USER" MYSQL_PASSWORD="$DB_PASS" \
  "$VENV_DIR/bin/python3" -c "from aipandit.db import DatabaseManager; m = DatabaseManager(); print('Initialized tables:', m.get_summary()['counts'])"

echo ""
echo "================================================================="
echo "AstroNaradMuni v1.4.0 is LIVE on https://${DOMAIN}"
echo "Admin DBMS summary: https://${DOMAIN}/api/v10/admin/users"
echo "phpMyAdmin tables:  users_profiles, chat_interactions, kundli_downloads, pandit_bookings"
echo "================================================================="
