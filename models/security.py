"""
Security utilities — input validation and sanitization for user-provided values.
"""
import ipaddress
import re
from typing import Optional, Tuple


DOMAIN_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$')


SUBDOMAIN_LABEL_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$')


def validate_ip_address(ip: str) -> Tuple[bool, str]:
    """
    Validate an IP address (IPv4 or IPv6).
    Returns (is_valid, error_message).
    """
    if not ip:
        return False, "IP address cannot be empty"

    ip = ip.strip()

    try:
        ipaddress.ip_address(ip)
        return True, ""
    except ValueError:
        return False, f"Invalid IP address format: {ip}"


def validate_domain_name(domain: str) -> Tuple[bool, str]:
    """
    Validate a full domain name (e.g., example.com, sub.example.com).
    Returns (is_valid, error_message).
    """
    if not domain:
        return False, "Domain name cannot be empty"

    domain = domain.strip().lower()


    if len(domain) > 253:
        return False, "Domain name too long (max 253 characters)"


    if not DOMAIN_PATTERN.match(domain):
        return False, f"Invalid domain name format: {domain}"


    if '..' in domain:
        return False, "Domain name cannot contain consecutive dots"


    labels = domain.split('.')
    for label in labels:
        if len(label) > 63:
            return False, f"Domain label too long: {label}"
        if label.startswith('-') or label.endswith('-'):
            return False, f"Domain label cannot start or end with hyphen: {label}"

    return True, ""


def validate_subdomain_label(label: str) -> Tuple[bool, str]:
    """
    Validate a subdomain label (single part without dots).
    Returns (is_valid, error_message).
    """
    if not label:
        return False, "Subdomain label cannot be empty"

    label = label.strip().lower()


    if len(label) > 63:
        return False, "Subdomain label too long (max 63 characters)"


    if not SUBDOMAIN_LABEL_PATTERN.match(label):
        return False, f"Invalid subdomain label format: {label}"


    if label.startswith('-') or label.endswith('-'):
        return False, "Subdomain label cannot start or end with hyphen"


    if label in ('localhost', 'test', 'example', 'invalid'):
        return False, f"Reserved subdomain label: {label}"

    return True, ""


def validate_subdomain_creation(subdomain: str, ip: str) -> Tuple[bool, str]:
    """
    Validate inputs for subdomain creation.
    Returns (is_valid, error_message).
    """

    is_valid, error = validate_subdomain_label(subdomain)
    if not is_valid:
        return False, f"Invalid subdomain: {error}"


    is_valid, error = validate_ip_address(ip)
    if not is_valid:
        return False, f"Invalid IP address: {error}"

    return True, ""


def sanitize_for_shell(value: str) -> str:
    """
    Sanitize a value for safe use in shell commands.
    Removes or escapes characters that could be used for command injection.
    """
    if not value:
        return ""


    dangerous = ['`', '$', '|', ';', '&', '<', '>', '\n', '\r', '\0']
    result = value
    for char in dangerous:
        result = result.replace(char, '')


    result = result.replace('"', "'").replace("'", "")

    return result.strip()


def sanitize_for_sed(value: str) -> str:
    """
    Sanitize a value for use in sed commands.
    Escapes special characters that could break sed syntax.
    """
    if not value:
        return ""


    special = r'[\.^$*+?{}\[\]\\|()]'
    result = re.sub(special, r'\\\g<0>', value)

    return result.strip()


def sanitize_path_component(path: str) -> str:
    """
    Sanitize a path component to prevent path traversal attacks.
    Removes slashes, dots, and other potentially dangerous characters.
    """
    if not path:
        return ""


    result = path.replace('..', '').replace('/', '').replace('\\', '')


    dangerous = ['`', '$', ';', '&', '|', '<', '>', '\n', '\r', '\0', '"', "'"]
    for char in dangerous:
        result = result.replace(char, '')

    return result.strip()


def validate_github_token(token: str) -> Tuple[bool, str]:
    """
    Validate a GitHub Personal Access Token format.
    Returns (is_valid, error_message).
    """
    if not token:
        return False, "GitHub token cannot be empty"

    token = token.strip()


    if len(token) < 10:
        return False, "GitHub token appears too short"


    if not re.match(r'^[a-zA-Z0-9_-]+$', token):
        return False, "GitHub token contains invalid characters"

    return True, ""


def sanitize_log_output(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input for safe logging.
    Truncates long values and removes control characters.
    """
    if not value:
        return ""


    result = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', value)


    if len(result) > max_length:
        result = result[:max_length] + "..."

    return result


class InputValidator:
    """Centralized input validation for the application."""

    @staticmethod
    def validate_subdomain_creation(subdomain: str, ip: str) -> Tuple[bool, str]:
        """
        Validate inputs for subdomain creation.
        Returns (is_valid, error_message).
        """

        is_valid, error = validate_subdomain_label(subdomain)
        if not is_valid:
            return False, f"Invalid subdomain: {error}"


        is_valid, error = validate_ip_address(ip)
        if not is_valid:
            return False, f"Invalid IP address: {error}"

        return True, ""

    @staticmethod
    def validate_domain_input(domain: str) -> Tuple[bool, str]:
        """
        Validate domain input for various operations.
        Returns (is_valid, error_message).
        """
        if not domain:
            return False, "Domain cannot be empty"

        domain = domain.strip().lower()


        if '.' in domain:
            return validate_domain_name(domain)
        else:
            return validate_subdomain_label(domain)

    @staticmethod
    def sanitize_all_inputs(**kwargs) -> dict:
        """
        Sanitize all provided keyword arguments.
        Returns a new dictionary with sanitized values.
        """
        sanitized = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                sanitized[key] = sanitize_for_shell(value)
            else:
                sanitized[key] = value
        return sanitized
