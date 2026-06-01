from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from datetime import datetime
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from django.core.management.base import BaseCommand
from django.utils import timezone

from company.models import Company
from currencies.models import Currency, ExchangeRate
from currencies.services import get_base_currency


API_BASE = "https://api.exchangerate.host"


def _fetch_rate_for_pair(base_currency_code: str, target_currency_code: str, date: str) -> Decimal | None:
    """Fetch rate from exchangerate.host for 1 unit of base_currency -> target_currency.

    We request the endpoint with `base={base_currency_code}` and `symbols={target_currency_code}`
    or use the historical date path if provided (YYYY-MM-DD or 'latest').
    Returns Decimal rate (target currency units per 1 base currency) or None on failure.
    """
    if not base_currency_code or not target_currency_code:
        return None
    path = date if date and date != "latest" else "latest"
    url = f"{API_BASE}/{path}?base={base_currency_code}&symbols={target_currency_code}"
    try:
        with urlopen(url, timeout=20) as resp:
            data = json.load(resp)
        if not data or not data.get("success", True):
            return None
        rates = data.get("rates") or {}
        r = rates.get(target_currency_code)
        if r is None:
            return None
        return Decimal(str(r))
    except (HTTPError, URLError, ValueError, InvalidOperation, Exception):
        return None


class Command(BaseCommand):
    help = "Fetch exchange rates from exchangerate.host and populate currencies.ExchangeRate rows (source=feed)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Date to fetch rates for (YYYY-MM-DD). Default: latest.",
            default="latest",
        )
        parser.add_argument(
            "--company",
            help="Company id to limit fetching to a single company (optional).",
            type=int,
            default=None,
        )

    def handle(self, *args, **options):
        date = options.get("date") or "latest"
        company_id = options.get("company")

        companies = Company.objects.all()
        if company_id:
            companies = companies.filter(pk=company_id)

        for comp in companies:
            # Respect company toggle if present
            try:
                if hasattr(comp, "exchange_rate_feeds_enabled") and not comp.exchange_rate_feeds_enabled:
                    self.stdout.write(f"Skipping company {comp} (feeds disabled)")
                    continue
            except Exception:
                pass

            base = get_base_currency(comp)
            if not base:
                self.stdout.write(f"No base currency for company {comp}; skipping")
                continue

            cur_qs = Currency.objects.filter(company=comp, is_active=True).exclude(pk=base.pk)
            if not cur_qs.exists():
                self.stdout.write(f"No non-base currencies for {comp}; skipping")
                continue

            # For each currency, request rate: 1 <currency> -> X base
            for cur in cur_qs:
                # we want 1 unit of cur -> how many units of base. Request base=cur, symbols=base.code
                fetched = _fetch_rate_for_pair(cur.code, base.code, date)
                if fetched is None:
                    self.stdout.write(f"Failed to fetch rate for {cur.code}->{base.code} for {comp} on {date}")
                    continue
                # effective_from: for 'latest' use today; for date use that date
                if date == "latest":
                    eff = timezone.now().date()
                else:
                    try:
                        eff = datetime.strptime(date, "%Y-%m-%d").date()
                    except Exception:
                        eff = timezone.now().date()

                # Store or update
                try:
                    ExchangeRate.objects.update_or_create(
                        currency=cur,
                        effective_from=eff,
                        defaults={"rate": fetched, "source": ExchangeRate.SOURCE_FEED},
                    )
                    self.stdout.write(f"Saved rate {cur.code} -> {base.code}: {fetched} (effective {eff}) for {comp}")
                except Exception as e:
                    self.stderr.write(f"DB save failed for {cur.code} on {eff}: {e}")
