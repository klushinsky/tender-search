"""
Offline tests for scripts/ted_search.py. The TED API is mocked, so these run
without network access:

    python -m unittest discover -s tests -v
"""
import io
import json
import os
import sys
import unittest
import urllib.error
from contextlib import redirect_stdout
from datetime import date, timedelta
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import ted_search as ts  # noqa: E402


def _notice(n, title="Polska – Usługi architektoniczne – Projekt szkoły w Krakowie",
            deadline_days=30, value=None, currency=None, ntype="cn-standard"):
    d = {
        "publication-number": f"{n:06d}-2026",
        "TI": {"pol": [title]},
        "AU": {"pol": ["Gmina Miejska Kraków"]},
        "CY": ["POL"],
        "PD": "2026-10-05+02:00",
        "notice-type": ntype,
    }
    if deadline_days is not None:
        d["DT"] = [(date.today() + timedelta(days=deadline_days)).isoformat() + "+02:00"]
    if value is not None:
        d["TV"] = [value]
    if currency:
        d["TV_CUR"] = [currency]
    return d


class FieldParsing(unittest.TestCase):
    def test_strips_country_and_service_prefix_only(self):
        t = "Deutschland – Architekturdienste – Neubau Schule – Bauabschnitt 2"
        self.assertEqual(ts._strip_ted_prefix(t), "Neubau Schule – Bauabschnitt 2")

    def test_title_without_prefix_is_untouched(self):
        self.assertEqual(ts._strip_ted_prefix("Masterplan - Phase 1 - Old Town"),
                         "Masterplan - Phase 1 - Old Town")

    def test_prefers_english_title(self):
        ti = {"pol": ["Polska – X – Szkoła"], "eng": ["Poland – X – School"]}
        self.assertEqual(ts.extract_title(ti), "School")

    def test_parse_date_formats(self):
        self.assertEqual(ts.parse_date("2026-10-20+02:00"), date(2026, 10, 20))
        self.assertEqual(ts.parse_date("2026-10-20T10:00:00Z"), date(2026, 10, 20))
        self.assertEqual(ts.parse_date(["2026-10-20-05:00"]), date(2026, 10, 20))
        self.assertIsNone(ts.parse_date("not a date"))

    def test_earliest_lot_deadline_wins(self):
        self.assertEqual(ts.extract_deadline(["2026-12-01Z", "2026-11-15Z"], None), date(2026, 11, 15))

    def test_value_conversion(self):
        self.assertAlmostEqual(ts.value_in_eur(425000, "PLN"), 100000, places=0)
        self.assertIsNone(ts.value_in_eur(1000, "XYZ"))
        self.assertIsNone(ts.value_in_eur(None, "EUR"))


class Search(unittest.TestCase):
    def _run(self, pages, **kw):
        with mock.patch.object(ts, "_post", side_effect=pages) as post:
            out = ts.search_ted(**kw)
        return out, post

    def test_paginates_until_short_page(self):
        page1 = {"notices": [_notice(i) for i in range(ts.PAGE_SIZE)]}
        page2 = {"notices": [_notice(1000 + i) for i in range(3)]}
        (results, stats, err), post = self._run([page1, page2], days_back=8)
        self.assertIsNone(err)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(post.call_args_list[0].args[0]["limit"], ts.PAGE_SIZE)
        self.assertEqual(post.call_args_list[1].args[0]["page"], 2)
        self.assertEqual(stats["fetched"], ts.PAGE_SIZE + 3)
        self.assertEqual(len(results), ts.PAGE_SIZE + 3)

    def test_filters_and_flags(self):
        page = {"notices": [
            _notice(1, value=100000, currency="EUR"),                 # below threshold -> drop
            _notice(2, value=2000000, currency="PLN"),                # ~470k EUR -> keep
            _notice(3, value=500000, currency="PLN"),                 # ~118k EUR -> drop
            _notice(4),                                               # no value -> keep
            _notice(5, value=10, currency="XYZ"),                     # unknown currency -> keep
            _notice(6, title="Sweden – X – HVAC upgrade"),  # MEP keyword -> drop
            _notice(7, deadline_days=5, ntype="cn-desg"),             # flagged, sorted first
            _notice(7),                                               # duplicate -> drop
            _notice(8, deadline_days=None),                           # no deadline -> last
        ]}
        (results, stats, err), _ = self._run([page], days_back=8, min_value_eur=250000)
        self.assertIsNone(err)
        kept = [r["url"].rsplit("/", 1)[-1] for r in results]
        self.assertEqual(kept[0], "000007-2026")
        self.assertEqual(kept[-1], "000008-2026")
        self.assertEqual(sorted(kept), ["000002-2026", "000004-2026", "000005-2026",
                                        "000007-2026", "000008-2026"])
        self.assertEqual(stats["skipped_value"], 2)
        self.assertEqual(stats["skipped_keyword"], 1)
        self.assertTrue(results[0]["deadline_soon"])
        self.assertEqual(results[0]["notice_type_label"], "Design contest")
        self.assertEqual(results[0]["title"], "Projekt szkoły w Krakowie")

    def test_http_error_returns_partial_results(self):
        page1 = {"notices": [_notice(i) for i in range(ts.PAGE_SIZE)]}
        err = urllib.error.HTTPError(ts.TED_API, 500, "boom", {}, io.BytesIO(b"server error"))
        (results, stats, error), _ = self._run([page1, err], days_back=8)
        self.assertIn("HTTP 500", error)
        self.assertEqual(len(results), ts.PAGE_SIZE)


class Cli(unittest.TestCase):
    def test_discord_output_and_json(self):
        page = {"notices": [_notice(1, deadline_days=3, value=300000, currency="EUR")]}
        with mock.patch.object(ts, "_post", return_value=page):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = ts.main(["8", "250000"])
            text = buf.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Found 1 notices", text)
            self.assertIn("⚠️", text)
            self.assertIn("300,000 EUR", text)
            self.assertIn("https://ted.europa.eu/en/notice/-/detail/000001-2026", text)

            buf = io.StringIO()
            with redirect_stdout(buf):
                ts.main(["8", "--json"])
            data = json.loads(buf.getvalue())
            self.assertEqual(data["stats"]["kept"], 1)
            self.assertEqual(data["results"][0]["value_eur"], 300000)


if __name__ == "__main__":
    unittest.main()
