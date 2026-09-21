from urllib.parse import urlparse

ALLOWED_BOOKING_HOSTS = {
    "www.google.com",
    "google.com",
    "www.amadeus.com",
    "amadeus.com",
    "www.skyscanner.co.in",
    "skyscanner.co.in",
    "www.booking.com",
    "booking.com",
}


def is_safe_outbound_url(value: str, allowed_hosts: set[str] | None = None) -> bool:
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    hosts = allowed_hosts or ALLOWED_BOOKING_HOSTS
    return parsed.scheme == "https" and parsed.hostname in hosts and not parsed.username
