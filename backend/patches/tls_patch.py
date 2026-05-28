"""Monkey-patch requests to bypass eastmoney TLS fingerprinting.

East Money (eastmoney.com) blocks Python requests/urllib3 JA3 TLS fingerprints.
This patches requests to use curl_cffi with browser TLS impersonation.
"""

import logging
import time
import random

logger = logging.getLogger(__name__)


def apply_patch():
    """Replace requests.get / requests.Session.get with curl_cffi versions."""
    try:
        from curl_cffi import requests as cffi_requests
        import requests

        def _do_request(url, max_retries=3, **kwargs):
            """Execute HTTP GET via curl_cffi with retry and fresh sessions."""
            kwargs.setdefault("timeout", 15)
            last_err = None
            for attempt in range(max_retries):
                try:
                    s = cffi_requests.Session(impersonate="chrome110")
                    resp = s.get(url, **kwargs)
                    resp.raise_for_status()
                    return resp
                except Exception as e:
                    last_err = e
                    if attempt < max_retries - 1:
                        delay = 2 * (attempt + 1) + random.uniform(0.5, 2.0)
                        time.sleep(delay)
            raise last_err

        def _patched_session_get(self, url, **kwargs):
            kwargs.pop("allow_redirects", None)
            return _do_request(url, **kwargs)

        def _patched_get(url, **kwargs):
            kwargs.pop("allow_redirects", None)
            return _do_request(url, **kwargs)

        requests.Session.get = _patched_session_get
        requests.get = _patched_get

        logger.info("TLS bypass patch applied: curl_cffi/chrome110 impersonation active")
    except ImportError:
        logger.warning(
            "curl_cffi not installed, TLS patch skipped. "
            "Install with: pip install curl_cffi"
        )
    except Exception as e:
        logger.error("Failed to apply TLS patch: %s", e)
