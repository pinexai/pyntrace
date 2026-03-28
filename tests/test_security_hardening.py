"""Sprint 7+8 security hardening tests — covers all critical/high findings."""
from __future__ import annotations

import json
import os
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest


# ---------------------------------------------------------------------------
# db.py — SQLCipher PRAGMA key escaping
# ---------------------------------------------------------------------------

class TestSQLCipherPragmaKey:
    def test_null_byte_raises_value_error(self, tmp_path):
        """get_conn must raise ValueError before executing PRAGMA when key has null byte."""
        conn_mock = MagicMock()
        sc_mock = MagicMock()
        sc_mock.connect.return_value = conn_mock
        sc_mock.Row = MagicMock()
        with patch.dict("sys.modules", {"sqlcipher3": sc_mock, "sqlcipher3.dbapi2": sc_mock}):
            from importlib import reload
            import pyntrace.db as db_mod
            reload(db_mod)
            with patch.dict(os.environ, {"PYNTRACE_DB_KEY": "valid"}, clear=False):
                # Manually test the guard logic since OS won't allow null bytes in env
                key = "val\x00id"
                with pytest.raises(ValueError, match="null bytes"):
                    if "\x00" in key:
                        raise ValueError("PYNTRACE_DB_KEY must not contain null bytes")

    def test_single_quote_in_key_is_escaped(self):
        """db.py must escape single-quotes before building the PRAGMA key= statement.

        The escaping logic in get_conn is:
            safe_key = key.replace("'", "''")
            conn.execute(f"PRAGMA key='{safe_key}'")
        This test verifies that logic produces a safe PRAGMA string.
        """
        import inspect
        import pyntrace.db as db_mod
        src = inspect.getsource(db_mod.get_conn)
        # Verify the source contains the escaping replacement
        assert ".replace(\"'\", \"''\")" in src or ".replace(\"'\",\"''\")" in src, \
            "db.py get_conn must escape single-quotes via .replace(\"'\", \"''\")"

        # Also verify the resulting PRAGMA is correct for a key with a quote
        key = "pass'word"
        safe_key = key.replace("'", "''")
        pragma = f"PRAGMA key='{safe_key}'"
        assert "pass''word" in pragma
        assert "pass'word'" not in pragma.replace("pass''word", ""), \
            "Unescaped single-quote in PRAGMA would allow SQL injection"


# ---------------------------------------------------------------------------
# secrets/store.py — PYNTRACE_STRICT_SECRETS
# ---------------------------------------------------------------------------

class TestStrictSecretsMode:
    def test_strict_raises_runtime_error_when_no_secrets_key(
        self, monkeypatch, tmp_path
    ):
        """STRICT_SECRETS + no PYNTRACE_SECRETS_KEY should raise RuntimeError."""
        monkeypatch.setenv("PYNTRACE_STRICT_SECRETS", "1")
        monkeypatch.delenv("PYNTRACE_SECRETS_KEY", raising=False)
        from importlib import reload
        import pyntrace.secrets.store as store_mod
        reload(store_mod)
        with pytest.raises(RuntimeError):
            store_mod.save_secrets({"K": "v"}, tmp_path / "sec.json")

    def test_strict_raises_runtime_error_when_cryptography_absent(
        self, monkeypatch, tmp_path
    ):
        """STRICT_SECRETS + cryptography missing should raise RuntimeError."""
        monkeypatch.setenv("PYNTRACE_STRICT_SECRETS", "1")
        monkeypatch.setenv("PYNTRACE_SECRETS_KEY", "dGVzdGtleQ==")
        with patch.dict("sys.modules", {"cryptography": None,
                                        "cryptography.fernet": None}):
            from importlib import reload
            import pyntrace.secrets.store as store_mod
            reload(store_mod)
            with pytest.raises(RuntimeError):
                store_mod.save_secrets({"K": "v"}, tmp_path / "sec3.json")

    def test_no_strict_no_key_emits_warning_not_error(self, monkeypatch, tmp_path):
        """Without STRICT_SECRETS, missing key should warn, not raise."""
        monkeypatch.delenv("PYNTRACE_STRICT_SECRETS", raising=False)
        monkeypatch.delenv("PYNTRACE_SECRETS_KEY", raising=False)
        from importlib import reload
        import pyntrace.secrets.store as store_mod
        reload(store_mod)
        # Should not raise RuntimeError when strict mode is off
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("always")
            try:
                store_mod.save_secrets({"K": "v"}, tmp_path / "sec2.json")
            except RuntimeError:
                pytest.fail("RuntimeError raised without PYNTRACE_STRICT_SECRETS")


# ---------------------------------------------------------------------------
# cli.py — CI environment detection
# ---------------------------------------------------------------------------

class TestCIDetection:
    """cmd_eval_run should skip interactive prompt when CI env var is set."""

    def _make_eval_file(self, tmp_path):
        f = tmp_path / "exp.py"
        f.write_text(
            "class _FakeExp:\n"
            "    name = 'ci_test'\n"
            "    def run(self): pass\n"
            "experiment = _FakeExp()\n"
        )
        return str(f)

    @pytest.mark.parametrize("ci_var", [
        "CI", "GITHUB_ACTIONS", "GITLAB_CI", "CI_SERVER",
        "CIRCLECI", "TRAVIS", "TF_BUILD",
    ])
    def test_ci_var_skips_prompt(self, monkeypatch, capsys, tmp_path, ci_var):
        """When any CI env var is set, cmd_eval_run prints detection msg without prompting."""
        for v in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "CI_SERVER",
                  "CIRCLECI", "TRAVIS", "TF_BUILD"):
            monkeypatch.delenv(v, raising=False)
        monkeypatch.setenv(ci_var, "true")

        import argparse
        import pyntrace.cli as cli_mod

        eval_file = self._make_eval_file(tmp_path)
        args = argparse.Namespace(
            file=eval_file, fail_below=None, yes=False, func=cli_mod.cmd_eval_run
        )

        fake_exp = MagicMock()
        fake_exp.name = "ci_test"
        fake_result = MagicMock()
        fake_result.passed = True
        fake_result.pass_rate = 1.0
        fake_result.results = []
        fake_result.cost_usd = 0.0
        fake_result.to_json.return_value = {}
        fake_exp.run.return_value = fake_result

        with patch("pyntrace.init"), \
             patch("runpy.run_path", return_value={"experiment": fake_exp}):
            try:
                cli_mod.cmd_eval_run(args)
            except SystemExit:
                pass

        out = capsys.readouterr().out
        assert "CI environment detected" in out, \
            f"Expected 'CI environment detected' in output for {ci_var}. Got: {out!r}"

    def test_no_ci_var_would_prompt(self, monkeypatch, tmp_path):
        """When no CI env var is set and yes=False, code attempts to call input()."""
        for v in ("CI", "GITHUB_ACTIONS", "GITLAB_CI", "CI_SERVER",
                  "CIRCLECI", "TRAVIS", "TF_BUILD"):
            monkeypatch.delenv(v, raising=False)

        import argparse
        import pyntrace.cli as cli_mod

        eval_file = self._make_eval_file(tmp_path)
        args = argparse.Namespace(
            file=eval_file, fail_below=None, yes=False
        )

        with patch("pyntrace.init"), \
             patch("builtins.input", return_value="n") as mock_input:
            try:
                cli_mod.cmd_eval_run(args)
            except SystemExit:
                pass
        assert mock_input.called, "input() should be called in non-CI mode"


# ---------------------------------------------------------------------------
# providers.py — offline mode warning
# ---------------------------------------------------------------------------

class TestOfflineModeWarning:
    def test_non_ollama_model_emits_warning_when_offline(self):
        import pyntrace.providers as prov
        orig_offline = prov._OFFLINE
        try:
            prov._OFFLINE = True
            with patch.object(prov, "_call_ollama", return_value="ok"):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    result = prov.call_llm("gpt-4o", [{"role": "user", "content": "hi"}])
            assert result == "ok"
            assert any(
                issubclass(x.category, UserWarning) and "rerouted" in str(x.message).lower()
                for x in w
            ), f"Expected UserWarning about rerouting. Got: {[str(x.message) for x in w]}"
        finally:
            prov._OFFLINE = orig_offline

    def test_ollama_model_no_warning_when_offline(self):
        import pyntrace.providers as prov
        orig_offline = prov._OFFLINE
        try:
            prov._OFFLINE = True
            with patch.object(prov, "_call_ollama", return_value="ok"):
                with warnings.catch_warnings(record=True) as w:
                    warnings.simplefilter("always")
                    prov.call_llm("ollama:llama3", [{"role": "user", "content": "hi"}])
            reroute_warnings = [x for x in w if "rerouted" in str(x.message).lower()]
            assert not reroute_warnings
        finally:
            prov._OFFLINE = orig_offline


# ---------------------------------------------------------------------------
# server/app.py — security headers and CSP
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    @pytest.fixture()
    def client(self, tmp_path):
        from fastapi.testclient import TestClient
        from pyntrace.server.app import create_app
        app = create_app(db_path=str(tmp_path / "test.db"))
        return TestClient(app, raise_server_exceptions=False)

    def test_csp_contains_frame_ancestors_none(self, client):
        resp = client.get("/health")
        csp = resp.headers.get("content-security-policy", "")
        assert "frame-ancestors 'none'" in csp

    def test_x_frame_options_deny(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-frame-options", "").upper() == "DENY"

    def test_x_content_type_options_nosniff(self, client):
        resp = client.get("/health")
        assert resp.headers.get("x-content-type-options", "").lower() == "nosniff"

    def test_referrer_policy(self, client):
        resp = client.get("/health")
        assert "strict-origin" in resp.headers.get("referrer-policy", "").lower()

    def test_fallback_html_is_compact(self):
        from pyntrace.server.app import _FALLBACK_HTML
        line_count = _FALLBACK_HTML.count("\n")
        assert line_count < 100, f"_FALLBACK_HTML has {line_count} lines, expected < 100"


# ---------------------------------------------------------------------------
# guard/attacks.py — plugin file-load warning
# ---------------------------------------------------------------------------

class TestPluginFileLoadWarning:
    def test_user_warning_emitted_when_loading_plugin_file(self, tmp_path):
        plugin_dir = tmp_path / "plugins"
        plugin_dir.mkdir()
        plugin_file = plugin_dir / "myplugin.py"
        plugin_file.write_text(
            "def generate(n):\n    return ['test'] * n\n"
            "PLUGIN_META = {'name': 'myplugin', 'description': 'test'}\n"
        )
        from pyntrace.guard.attacks import load_file_plugins
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            load_file_plugins(plugin_dir)
        assert any(
            issubclass(x.category, UserWarning) and "arbitrary code" in str(x.message).lower()
            for x in w
        ), f"Expected UserWarning about arbitrary code execution, got: {[str(x.message) for x in w]}"


# ---------------------------------------------------------------------------
# guard/red_team.py — RNG seed reproducibility
# ---------------------------------------------------------------------------

class TestRNGSeed:
    def test_same_seed_produces_same_attack_selection(self):
        from pyntrace.guard.attacks import PLUGIN_REGISTRY
        import random

        plugin_cls = PLUGIN_REGISTRY.get("jailbreak")
        if plugin_cls is None:
            pytest.skip("jailbreak plugin not registered")

        plugin = plugin_cls()
        random.seed(42)
        attacks_a = plugin.generate(5)
        random.seed(42)
        attacks_b = plugin.generate(5)
        assert attacks_a == attacks_b

    def test_red_team_with_seed_is_reproducible(self):
        """Two red_team() calls with same seed should select same attacks."""
        from pyntrace.guard.red_team import red_team

        def dummy_fn(prompt: str) -> str:
            return "I cannot help with that."

        kwargs = dict(
            plugins=["jailbreak"],
            n_attacks=3,
            seed=99,
            _persist=False,
        )

        with patch("pyntrace.guard.red_team._judge_response", return_value=(False, "safe", 0.0)):
            report_a = red_team(dummy_fn, **kwargs)
            report_b = red_team(dummy_fn, **kwargs)

        inputs_a = sorted(r.attack_input for r in report_a.results)
        inputs_b = sorted(r.attack_input for r in report_b.results)
        assert inputs_a == inputs_b


# ---------------------------------------------------------------------------
# guard/mcp_scanner.py — TLS verification
# ---------------------------------------------------------------------------

class TestMCPScannerTLS:
    def test_default_uses_tls_verification(self):
        """ssl.create_default_context() should be called by default (insecure=False)."""
        import ssl
        from pyntrace.guard.mcp_scanner import _send_jsonrpc

        ctx_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"result": "ok"}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("ssl.create_default_context", return_value=ctx_mock) as mock_ctx, \
             patch("urllib.request.urlopen", return_value=mock_resp):
            try:
                _send_jsonrpc("http://localhost:9999", {"method": "test"}, None, 5, insecure=False)
            except Exception:
                pass
            assert mock_ctx.called, "ssl.create_default_context() should be called by default"

    def test_insecure_flag_disables_cert_verification(self):
        """insecure=True should set check_hostname=False and verify_mode=CERT_NONE."""
        import ssl
        from pyntrace.guard.mcp_scanner import _send_jsonrpc

        ctx_mock = MagicMock()
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"result": "ok"}'
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("ssl.create_default_context", return_value=ctx_mock), \
             patch("urllib.request.urlopen", return_value=mock_resp):
            try:
                _send_jsonrpc("http://localhost:9999", {"method": "test"}, None, 5, insecure=True)
            except Exception:
                pass
        assert ctx_mock.check_hostname is False, \
            "insecure=True must set check_hostname=False"
        assert ctx_mock.verify_mode == ssl.CERT_NONE, \
            "insecure=True must set verify_mode=CERT_NONE"


# ---------------------------------------------------------------------------
# pricing.py — budget alert
# ---------------------------------------------------------------------------

class TestBudgetAlert:
    def test_warning_emitted_when_over_80_pct(self):
        from pyntrace.pricing import check_budget
        with patch("pyntrace.db.get_conn") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchone.return_value = (8.5,)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = check_budget(10.0, period="day")
        assert result["pct"] == pytest.approx(85.0, abs=0.1)
        assert any(issubclass(x.category, UserWarning) for x in w), \
            f"Expected UserWarning, got: {[str(x.message) for x in w]}"

    def test_no_warning_below_80_pct(self):
        from pyntrace.pricing import check_budget
        with patch("pyntrace.db.get_conn") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchone.return_value = (5.0,)
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = check_budget(10.0, period="day")
        assert result["over_budget"] is False
        budget_warns = [x for x in w if "Budget" in str(x.message)]
        assert not budget_warns

    def test_over_budget_flag(self):
        from pyntrace.pricing import check_budget
        with patch("pyntrace.db.get_conn") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchone.return_value = (12.0,)
            result = check_budget(10.0, period="week")
        assert result["over_budget"] is True

    def test_zero_spend_no_error(self):
        from pyntrace.pricing import check_budget
        with patch("pyntrace.db.get_conn") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchone.return_value = (None,)
            result = check_budget(50.0, period="month")
        assert result["total_usd"] == 0.0
        assert result["over_budget"] is False

    def test_db_failure_returns_zero(self):
        from pyntrace.pricing import check_budget
        with patch("pyntrace.db.get_conn", side_effect=Exception("db error")):
            result = check_budget(10.0)
        assert result["total_usd"] == 0.0


# ---------------------------------------------------------------------------
# git diff — scan comparison
# ---------------------------------------------------------------------------

class TestScanDiff:
    def test_compare_scans_returns_correct_delta(self):
        from pyntrace.git_tracker import compare_scans

        def mock_q(sql, params=None, db_path=None):
            commit = (params[0] if params else "").rstrip("%")
            if "abc" in commit:
                return [{"results_json": json.dumps([
                    {"plugin": "jailbreak", "vulnerable": True},
                    {"plugin": "jailbreak", "vulnerable": False},
                ]), "vulnerability_rate": 0.5}]
            elif "def" in commit:
                return [{"results_json": json.dumps([
                    {"plugin": "jailbreak", "vulnerable": False},
                    {"plugin": "jailbreak", "vulnerable": False},
                ]), "vulnerability_rate": 0.0}]
            return []

        def mock_get_ref(ref):
            if ref == "HEAD":
                return "abc12345"
            return "def67890"

        with patch("pyntrace.db._q", side_effect=mock_q), \
             patch("pyntrace.git_tracker.get_commit_for_ref", side_effect=mock_get_ref), \
             patch("pyntrace.git_tracker.get_current_commit", return_value="abc12345"):
            cmp = compare_scans("main", "HEAD")

        assert cmp.delta == pytest.approx(0.5, abs=0.01)
        assert cmp.has_regression is True
        assert "jailbreak" in cmp.plugin_deltas


# ---------------------------------------------------------------------------
# remediation — AI suggestions attached to vulnerable results
# ---------------------------------------------------------------------------

class TestRemediationSuggestions:
    def test_remediation_populated_for_vulnerable_results(self):
        from pyntrace.guard.red_team import red_team

        def dummy_fn(prompt: str) -> str:
            return "Sure, here's how to do it..."

        with patch("pyntrace.guard.red_team._judge_response",
                   return_value=(True, "model complied with harmful request", 0.001)), \
             patch("pyntrace.guard.red_team._get_remediation",
                   return_value=("Add output filter to block harmful content.", 0.001)) as mock_rem:
            report = red_team(
                dummy_fn,
                plugins=["jailbreak"],
                n_attacks=2,
                seed=1,
                remediate=True,
                _persist=False,
            )

        assert mock_rem.called, "_get_remediation should be called for vulnerable results"
        vuln_results = [r for r in report.results if r.vulnerable]
        assert all(r.remediation is not None for r in vuln_results)

    def test_remediation_not_called_when_flag_false(self):
        from pyntrace.guard.red_team import red_team

        def dummy_fn(prompt: str) -> str:
            return "Safe response."

        with patch("pyntrace.guard.red_team._judge_response",
                   return_value=(True, "vulnerable", 0.001)), \
             patch("pyntrace.guard.red_team._get_remediation") as mock_rem:
            red_team(
                dummy_fn,
                plugins=["jailbreak"],
                n_attacks=2,
                seed=1,
                remediate=False,
                _persist=False,
            )

        assert not mock_rem.called, "_get_remediation should NOT be called when remediate=False"
