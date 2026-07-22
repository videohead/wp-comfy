#!/bin/bash
# Database setup script for Lando environment
# Run with: ./scripts/setup-db.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

TARGET_URL="${TARGET_URL:-https://videohead.duckdns.org}"
BACKUP_FILE="${BACKUP_FILE:-$PROJECT_ROOT/backup.sql}"

if ! command -v lando >/dev/null 2>&1; then
    echo "Error: lando is not installed or not in PATH."
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: backup file not found at $BACKUP_FILE"
    exit 1
fi

echo "=== WordPress Comfy Database Setup ==="

# Create database user if not exists
lando mariadb -u root -proot <<'SQL'
CREATE USER IF NOT EXISTS 'wordpress'@'%' IDENTIFIED BY 'wordpress';
GRANT ALL PRIVILEGES ON *.* TO 'wordpress'@'%';
FLUSH PRIVILEGES;
SQL

# Create database if not exists
lando mariadb -u root -proot -e "CREATE DATABASE IF NOT EXISTS wordpress CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" 2>&1 || true

# Import backup.sql (skip if already imported)
TABLE_COUNT=$(lando mariadb -u wordpress -pwordpress -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='wordpress';" 2>/dev/null | tail -1)
if [ "$TABLE_COUNT" = "0" ] || [ -z "$TABLE_COUNT" ]; then
    echo "Importing $BACKUP_FILE..."
    lando mariadb -u root -proot wordpress < "$BACKUP_FILE" 2>&1
    echo "Backup imported successfully."
else
    echo "Database already has $TABLE_COUNT tables. Skipping import."
fi

# Set canonical WordPress site URL values
lando mariadb -u wordpress -pwordpress -e "UPDATE wordpress.wp_options SET option_value='${TARGET_URL}' WHERE option_name IN ('siteurl', 'home');"

# Use wp-cli so serialized values remain valid when replacing old hostnames.
lando wp search-replace "http://videohead.duckdns.org" "${TARGET_URL}" --all-tables --skip-columns=guid --precise
lando wp search-replace "https://wordpresscomfy.lndo.site" "${TARGET_URL}" --all-tables --skip-columns=guid --precise
lando wp search-replace "http://wordpresscomfy.lndo.site" "${TARGET_URL}" --all-tables --skip-columns=guid --precise

echo "=== Database setup complete ==="
echo "WordPress URL: $TARGET_URL"
echo ""
echo "After lando rebuild, run: ./scripts/setup-db.sh"
