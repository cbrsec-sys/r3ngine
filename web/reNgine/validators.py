import re
import ipaddress
import socket
import urllib.parse

import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

_BLOCKED_NETS = [
    ipaddress.ip_network('10.0.0.0/8'),
    ipaddress.ip_network('172.16.0.0/12'),
    ipaddress.ip_network('192.168.0.0/16'),
    ipaddress.ip_network('127.0.0.0/8'),
    ipaddress.ip_network('169.254.0.0/16'),
    ipaddress.ip_network('0.0.0.0/8'),
    ipaddress.ip_network('::1/128'),
    ipaddress.ip_network('fc00::/7'),
]


def validate_external_url(url: str, allowed_schemes=('https', 'http')) -> str:
    """Validate that a URL is safe for server-side HTTP requests.

    Raises ValueError for private/loopback/metadata addresses, dangerous schemes,
    or unparseable input. Returns the original url string on success.
    """
    if not url:
        raise ValueError('URL must not be empty')

    parsed = urllib.parse.urlparse(url)

    if parsed.scheme not in allowed_schemes:
        raise ValueError(f'URL scheme {parsed.scheme!r} is not allowed (must be https or http)')

    hostname = parsed.hostname
    if not hostname:
        raise ValueError('URL must contain a valid hostname')

    try:
        resolved = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        raise ValueError(f'Cannot resolve hostname {hostname!r}')

    for _family, _type, _proto, _canonname, sockaddr in resolved:
        raw_addr = sockaddr[0]
        try:
            addr = ipaddress.ip_address(raw_addr)
        except ValueError:
            continue
        for net in _BLOCKED_NETS:
            if addr in net:
                raise ValueError(
                    f'URL {hostname!r} resolves to a blocked address ({addr})'
                )

    return url


def validate_domain(value):
    if not validators.domain(value):
        raise ValidationError(_('%(value)s is not a valid domain Name'
                                ), params={'value': value})


def validate_url(value):
    if not validators.url(value):
        raise ValidationError(_('%(value)s is not a valid URL Name'),
                              params={'value': value})


def validate_short_name(value):
    regex = re.compile(r'[@!#$%^&*()<>?/\|}{~:]')
    if regex.search(value):
        raise ValidationError(_('%(value)s is not a valid short name,'
                                + ' can only contain - and _'),
                              params={'value': value})
