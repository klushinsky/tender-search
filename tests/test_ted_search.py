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


def _notice(n, title=None, deadline_days=30, value=None, currency=None, ntype="cn-standard"):
    if title is None:  # unique per notice so de-duplication leaves them alone
        title = f"Polska – Usługi architektoniczne – Projekt szkoły nr {n} w Krakowie"
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

    def test_earliest_upcoming_lot_deadline_wins(self):
        today = date(2026, 10, 9)
        self.assertEqual(ts.extract_deadline(["2026-12-01Z", "2026-11-15Z"], None, today), date(2026, 11, 15))
        # a stale lot date in the past is ignored when an upcoming one exists
        self.assertEqual(ts.extract_deadline(["2026-07-07Z", "2026-11-15Z"], None, today), date(2026, 11, 15))
        # all dates past: return the latest so the caller can drop it as expired
        self.assertEqual(ts.extract_deadline(["2026-07-07Z", "2026-07-17Z"], None, today), date(2026, 7, 17))

    def test_value_conversion(self):
        self.assertAlmostEqual(ts.value_in_eur(425000, "PLN"), 100000, places=0)
        self.assertIsNone(ts.value_in_eur(1000, "XYZ"))
        self.assertIsNone(ts.value_in_eur(None, "EUR"))


class Relevance(unittest.TestCase):
    def score(self, title, ntype="cn-standard"):
        return ts.relevance(title, ntype)[0]

    def test_architecture_titles_score_positive(self):
        for title in [
            "Concours restreint de ma\u00eetrise d\u2019\u0153uvre pour une m\u00e9diath\u00e8que",
            "Generalplanungsleistungen f\u00fcr die Gemeinschaftsgrundschule Sonsbeck",
            "Przebudowa szko\u0142y podstawowej nr 3",
            "St\u00e4dtebaulich-freiraumplanerischer Wettbewerb",
            "Het aanstellen van een architect voor ontwerp",
        ]:
            self.assertGreater(self.score(title), 0, title)

    def test_engineering_titles_score_negative(self):
        for title in [
            "Pe\u0142nienie funkcji In\u017cyniera Kontraktu nad realizacj\u0105 zada\u0144",
            "Augšdaugavas novada ceļu atjaunošanas būvuzraudzības pakalpojumi",
            "Redacci\u00f3n del proyecto de se\u00f1alizaci\u00f3n ferroviaria",
            "Vermessungsleistungen, Ingenieurvermessung Kanalnetz",
        ]:
            self.assertLess(self.score(title), 0, title)

    def test_short_stems_only_match_word_starts(self):
        # "^trate" must not hit "strategie", "^cultu" must not hit "agriculture"
        self.assertEqual(ts.relevance("Strategie f\u00fcr Agriculture")[2], [])
        self.assertEqual(ts.relevance("Strategie f\u00fcr Agriculture")[1], [])

    def test_design_contest_bonus(self):
        self.assertEqual(self.score("Mitte 15 / Westbahnhof", "cn-desg"), 3)


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
            _notice(9, deadline_days=-3),                             # deadline passed -> drop
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
        self.assertEqual(stats["skipped_expired"], 1)
        self.assertTrue(results[0]["deadline_soon"])
        self.assertEqual(results[0]["notice_type_label"], "Design contest")
        self.assertEqual(results[0]["title"], "Projekt szkoły nr 7 w Krakowie")

    def test_http_error_returns_partial_results(self):
        page1 = {"notices": [_notice(i) for i in range(ts.PAGE_SIZE)]}
        err = urllib.error.HTTPError(ts.TED_API, 500, "boom", {}, io.BytesIO(b"server error"))
        (results, stats, error), _ = self._run([page1, err], days_back=8)
        self.assertIn("HTTP 500", error)
        self.assertEqual(len(results), ts.PAGE_SIZE)


class Duplicates(unittest.TestCase):
    def test_keeps_latest_publication_of_same_tender(self):
        same = "Polska – X – Szkoła podstawowa"
        page = {"notices": [_notice(5, title=same), _notice(9, title=same), _notice(7, title="Other")]}
        with mock.patch.object(ts, "_post", return_value=page):
            results, stats, _ = ts.search_ted(8)
        self.assertEqual(stats["duplicates"], 1)
        urls = sorted(r["url"].rsplit("/", 1)[-1] for r in results)
        self.assertEqual(urls, ["000007-2026", "000009-2026"])


class Selection(unittest.TestCase):
    def test_limit_and_all(self):
        results = [{"relevance": s} for s in (5, 3, 1, 0, -2)]
        self.assertEqual([r["relevance"] for r in ts.select(results, limit=2)], [5, 3])
        self.assertEqual([r["relevance"] for r in ts.select(results)], [5, 3, 1])
        self.assertEqual(len(ts.select(results, show_all=True)), 5)


class Cli(unittest.TestCase):
    def test_discord_output_and_json(self):
        page = {"notices": [_notice(1, deadline_days=3, value=300000, currency="EUR")]}
        with mock.patch.object(ts, "_post", return_value=page):
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = ts.main(["8", "250000"])
            text = buf.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("Found 1 open notices", text)
            self.assertIn("1 look like architecture", text)
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
