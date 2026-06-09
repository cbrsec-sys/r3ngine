import ipaddress
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from rest_framework import serializers

from reNgine.definitions import TARGET_TYPE_CHOICES

_VALID_TARGET_TYPES = [code for code, _ in TARGET_TYPE_CHOICES]


def _validate_cidr(value: str) -> None:
    try:
        ipaddress.ip_network(value, strict=False)
    except ValueError:
        raise serializers.ValidationError("Invalid CIDR range. Expected format: 192.168.1.0/24")


def _validate_email_address(value: str) -> None:
    try:
        validate_email(value)
    except DjangoValidationError:
        raise serializers.ValidationError("Invalid email address format.")


def _validate_username(value: str) -> None:
    if not re.match(r'^[a-zA-Z0-9_.\-@+]+$', value):
        raise serializers.ValidationError(
            "Username contains invalid characters. Allowed: letters, digits, _, ., -, @, +"
        )


def _validate_ip_address(value: str) -> None:
    try:
        ipaddress.ip_address(value)
    except ValueError:
        raise serializers.ValidationError("Invalid IP address format.")


_TYPE_VALIDATORS = {
    'cidr': _validate_cidr,
    'email': _validate_email_address,
    'username': _validate_username,
    'ip': _validate_ip_address,
}


class AddTargetSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=2048)
    target_type = serializers.ChoiceField(choices=_VALID_TARGET_TYPES, default='domain')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    organization = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        name = data.get('name', '').strip()
        target_type = data.get('target_type', 'domain')
        if target_type in _TYPE_VALIDATORS:
            try:
                _TYPE_VALIDATORS[target_type](name)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'name': exc.detail})
        return data
