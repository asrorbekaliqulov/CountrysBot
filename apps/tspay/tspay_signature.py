"""TSPay webhook imzo tekshiruvi (docs: X-Timestamp + X-Signature: sha256=...)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


def webhook_secret() -> str:
    return (
        getattr(settings, 'TSPAY_WEBHOOK_SECRET', None)
        or os.getenv('TSPAY_WEBHOOK_SECRET', '')
        or ''
    )


def build_signature_message(order_id, amount, timestamp: str) -> str:
    """HMAC payload: order_id:amount:timestamp (docs)."""
    oid = '' if order_id is None else str(order_id)
    amt = int(round(float(amount)))
    return f'{oid}:{amt}:{timestamp}'


def sign_message(secret: str, message: str) -> str:
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f'sha256={digest}'


def verify_tspay_webhook_signature(
    meta: dict,
    *,
    order_id,
    amount,
    timestamp: str | None = None,
) -> bool:
    secret = webhook_secret()
    if not secret:
        logger.warning('[TSPay] TSPAY_WEBHOOK_SECRET yo\'q — imzo tekshiruvi o\'tkazildi.')
        return True

    sig_header = (meta.get('HTTP_X_SIGNATURE') or '').strip()
    ts = (timestamp or meta.get('HTTP_X_TIMESTAMP') or '').strip()
    if not sig_header or not ts:
        logger.warning('[TSPay] X-Signature yoki X-Timestamp yo\'q.')
        return False

    message = build_signature_message(order_id, amount, ts)
    expected = sign_message(secret, message)

    if hmac.compare_digest(sig_header, expected):
        return True

    # Ba'zan faqat hex qismi kelishi mumkin
    received_hex = sig_header[7:] if sig_header.lower().startswith('sha256=') else sig_header
    expected_hex = expected[7:]
    if hmac.compare_digest(received_hex, expected_hex):
        return True

    logger.warning(
        '[TSPay] Imzo mos kelmadi oid=%s amt=%s ts=%s',
        order_id,
        int(round(float(amount))),
        ts,
    )
    return False
