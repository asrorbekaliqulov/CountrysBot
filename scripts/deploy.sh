#!/usr/bin/env bash
# Production deploy — GitHub Actions yoki qo'lda ishga tushiring.
set -euo pipefail

APP_DIR="${APP_DIR:-/var/www/CountrysBot}"
BRANCH="${DEPLOY_BRANCH:-main}"
VENV="${APP_DIR}/venv"

log() { echo "[deploy] $*"; }

if [[ ! -d "$APP_DIR/.git" ]]; then
  log "XATO: $APP_DIR git repo emas"
  exit 1
fi

cd "$APP_DIR"

if [[ -f .env ]]; then
  cp -a .env ".env.bak.$(date +%Y%m%d_%H%M%S)"
  log ".env zaxiralandi"
fi

log "Git: origin/$BRANCH"
git fetch origin "$BRANCH"
git reset --hard "origin/$BRANCH"

if [[ ! -d "$VENV" ]]; then
  log "venv yaratilmoqda..."
  python3 -m venv "$VENV"
fi

# shellcheck source=/dev/null
source "${VENV}/bin/activate"

pip install -q --upgrade pip
pip install -q -r requirements.txt

log "migrate"
python manage.py migrate --noinput

log "collectstatic"
python manage.py collectstatic --noinput

log "systemd restart"
systemctl restart gunicorn
systemctl restart telegram_bot

if systemctl is-active --quiet gunicorn && systemctl is-active --quiet telegram_bot; then
  log "Tayyor — gunicorn va telegram_bot ishlayapti"
else
  log "XATO: servislar active emas"
  systemctl status gunicorn telegram_bot --no-pager || true
  exit 1
fi
