import json
from typing import Iterable, Optional
from email.utils import parseaddr

import requests
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage, EmailMultiAlternatives
from django.conf import settings


class MailtrapAPIEmailBackend(BaseEmailBackend):
    """
    Sends emails via Mailtrap Email Sending HTTP API.
    Requires settings:
      - MAILTRAP_API_TOKEN
      - MAILTRAP_API_URL (default: https://send.api.mailtrap.io/api/send)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_token = getattr(settings, 'MAILTRAP_API_TOKEN', None)
        self.api_url = getattr(settings, 'MAILTRAP_API_URL', 'https://send.api.mailtrap.io/api/send')

    def send_messages(self, email_messages: Iterable[EmailMessage]) -> int:
        if not email_messages:
            return 0
        if not self.api_token:
            if self.fail_silently:
                return 0
            raise ValueError('MAILTRAP_API_TOKEN is not configured')

        sent_count = 0
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
        }

        for message in email_messages:
            try:
                from_name, from_email = self._split_from(message.from_email or settings.DEFAULT_FROM_EMAIL)
                to_list = [{'email': addr} for addr in message.to or []]
                cc_list = [{'email': addr} for addr in (message.cc or [])]
                bcc_list = [{'email': addr} for addr in (message.bcc or [])]

                text_part: Optional[str] = None
                html_part: Optional[str] = None

                if isinstance(message, EmailMultiAlternatives) and message.alternatives:
                    # Look for HTML alternative
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            html_part = content
                            break
                # The main body is usually text/plain
                text_part = message.body or None

                payload = {
                    'from': {
                        'email': from_email,
                        'name': from_name or '',
                    },
                    'to': to_list,
                    'cc': cc_list or None,
                    'bcc': bcc_list or None,
                    'subject': message.subject or '',
                }
                if html_part is not None:
                    payload['html'] = html_part
                if text_part is not None:
                    payload['text'] = text_part

                # Remove None keys
                payload = {k: v for k, v in payload.items() if v}

                resp = requests.post(self.api_url, headers=headers, data=json.dumps(payload), timeout=10)
                if 200 <= resp.status_code < 300:
                    sent_count += 1
                else:
                    if not self.fail_silently:
                        raise RuntimeError(f'Mailtrap API error {resp.status_code}: {resp.text}')
            except Exception:
                if not self.fail_silently:
                    raise
        return sent_count

    @staticmethod
    def _split_from(from_field: str):
        name, email = parseaddr(from_field)
        return name, email or from_field
