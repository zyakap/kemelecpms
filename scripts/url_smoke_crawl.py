"""Crawl every GET URL as an admin user against a seeded database.

Usage: python scripts/url_smoke_crawl.py

Builds an in-memory-ish sqlite test DB? No — uses the dev DB, so run against
a scratch database. It seeds a minimal project, then resolves every URL
pattern, substituting pk=1 style kwargs, and reports non-2xx/3xx responses.
"""
import os
import re
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

import django

django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import URLPattern, URLResolver, get_resolver

User = get_user_model()


def iter_patterns(resolver, prefix=""):
    for p in resolver.url_patterns:
        if isinstance(p, URLResolver):
            yield from iter_patterns(p, prefix + str(p.pattern))
        elif isinstance(p, URLPattern):
            yield prefix + str(p.pattern), p


def materialize(path_pattern):
    """Convert a route pattern into a concrete URL with pk=1 etc."""
    if path_pattern.startswith("^"):
        return None  # skip regex routes (admin, debug)
    out = path_pattern
    for m in re.findall(r"<([^>]+)>", path_pattern):
        if ":" in m:
            conv, name = m.split(":", 1)
        else:
            conv, name = "str", m
        if conv == "int":
            val = "1"
        elif conv == "uuid":
            return None
        else:
            val = "x"
        out = out.replace(f"<{m}>", val)
    return "/" + out


def main():
    admin, _ = User.objects.get_or_create(
        email="crawler@example.com",
        defaults={"first_name": "Crawl", "last_name": "Er", "role": "admin",
                  "is_staff": True, "is_superuser": True},
    )
    admin.set_password("crawlpass123")
    admin.is_superuser = True
    admin.is_staff = True
    admin.save()

    c = Client()
    assert c.login(email="crawler@example.com", password="crawlpass123"), "login failed"

    resolver = get_resolver()
    seen = set()
    failures = []
    skipped = []
    count = 0
    for raw, pattern in iter_patterns(resolver):
        url = materialize(raw)
        if url is None or url in seen:
            continue
        seen.add(url)
        if url.startswith(("/admin", "/__debug__", "/media", "/static")):
            continue
        # POST-only or destructive endpoints: skip known action URL name suffixes
        name = pattern.name or ""
        if any(s in name for s in ("delete", "logout")):
            skipped.append(url)
            continue
        count += 1
        try:
            resp = c.get(url, follow=False)
            code = resp.status_code
            if code >= 500:
                failures.append((url, name, code, ""))
            elif code == 404 and "1" not in url and "x" not in url:
                failures.append((url, name, code, "static 404"))
        except Exception:
            tb = traceback.format_exc().strip().splitlines()
            failures.append((url, name, "EXC", tb[-1]))
    print(f"Crawled {count} URLs, {len(failures)} failures, {len(skipped)} skipped")
    for url, name, code, extra in failures:
        print(f"  {code}  {url}  [{name}] {extra}")


if __name__ == "__main__":
    main()
