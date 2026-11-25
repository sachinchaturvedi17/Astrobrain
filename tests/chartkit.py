"""Test helpers: build charts with exact placements (no ephemeris) and run the rule base."""
from dataclasses import replace

from aipandit.derive import enrich
from aipandit.engines.base import RawChart, RawPlanet
from aipandit.engines.vedaksha_engine import VedakshaEngine
from aipandit.inference import infer
from aipandit.intake import BirthInput
from aipandit.jyotish import GRAHAS
from aipandit.kundli import generate_kundli
from aipandit.rulepacks import parashari_rules

RULES = parashari_rules()
_real = VedakshaEngine()


class FixedEngine:
    """Returns exactly the placements it is given. Dasha is delegated to the real engine."""
    lagna_error_arcsec = _real.lagna_error_arcsec
    planet_error_arcsec = _real.planet_error_arcsec
    dasha_year_days = _real.dasha_year_days
    engine_id = "fixed:test"

    def __init__(self, lagna_lon, lons):
        self.lagna_lon, self.lons = lagna_lon, lons

    def natal(self, jd_ut, lat, lon, *, ayanamsa, node_mode):
        planets = {g: RawPlanet(g, self.lons[g], 1.0, False) for g in GRAHAS}
        return RawChart(jd_ut, planets, self.lagna_lon, (self.lagna_lon + 90) % 360, self.engine_id)

    def vimshottari(self, birth_jd, moon_longitude, depth=2):
        return _real.vimshottari(birth_jd, moon_longitude, depth)


BIRTH = BirthInput(name="t", date="1990-05-15", time="14:30", time_certainty="exact",
                   place_name="Bhopal", latitude=23.2599, longitude=77.4126,
                   tz_name="Asia/Kolkata", subject_is_minor=False)


def make(lagna, signs=None, lons=None, birth=BIRTH):
    """lagna: sign index. signs: {graha: sign index} placed mid-sign. lons: {graha: absolute longitude}.
    Unspecified grahas default to Mesha mid-sign; Ketu defaults to Rahu + 180."""
    full = {g: 15.0 for g in GRAHAS}
    for g, s in (signs or {}).items():
        full[g] = s * 30 + 15.0
    full.update(lons or {})
    if "Ketu" not in (signs or {}) and "Ketu" not in (lons or {}):
        full["Ketu"] = (full["Rahu"] + 180.0) % 360
    k = generate_kundli(birth, engine=FixedEngine(lagna * 30 + 15.0, full))
    return k, enrich(k)


def fired(store, rules=RULES):
    return infer(store, rules).fired_ids()


MESHA, VRISHABHA, MITHUNA, KARKA, SIMHA, KANYA, TULA, VRISCHIKA, DHANU, MAKARA, KUMBHA, MEENA = range(12)


def _install_unittest_pytest_bridge() -> None:
    """Allow `python -m unittest` to run pytest-style test modules seamlessly (with or without pytest 9.x installed)."""
    import atexit
    import contextlib
    import inspect
    import math
    import os
    import re
    import sys
    import tempfile
    import types
    import unittest
    import warnings

    warnings.simplefilter("ignore", ResourceWarning)

    # If the real pytest CLI runner is driving this process, do not install the unittest bridge.
    if "_pytest.main" in sys.modules and "unittest" not in sys.argv[0]:
        return

    class _RaisesCtx:
        def __init__(self, exc_type, match=None):
            self.exc_type = exc_type
            self.match = match
            self.value = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, tb):
            if exc_type is None:
                raise AssertionError(f"DID NOT RAISE {self.exc_type}")
            if not issubclass(exc_type, self.exc_type):
                return False
            self.value = exc_val
            try:
                if self.match and not re.search(self.match, str(exc_val)):
                    raise AssertionError(f"{self.match!r} did not match {str(exc_val)!r}")
            finally:
                if hasattr(exc_val, "close") and callable(exc_val.close):
                    try:
                        exc_val.close()
                    except Exception:
                        pass
            return True

    class _Approx:
        def __init__(self, val, abs=1e-6, rel=1e-6):
            self.val, self.abs, self.rel = val, abs, rel

        def __eq__(self, other):
            return math.isclose(other, self.val, rel_tol=self.rel, abs_tol=self.abs)

    class _Mark:
        @staticmethod
        def parametrize(names, values):
            argnames = [x.strip() for x in names.split(",")] if isinstance(names, str) else list(names)

            def dec(fn):
                existing = list(getattr(fn, "_parametrize", []))
                fn._parametrize = existing + [(argnames, list(values))]
                return fn
            return dec

        def __getattr__(self, _name):
            def dec(fn):
                return fn
            return dec

    def fixture(fn=None, *, scope="function", **_kw):
        def dec(f):
            f._is_fixture = True
            f._fixture_scope = scope
            return f
        return dec(fn) if fn is not None else dec

    def importorskip(name, **_kw):
        try:
            return __import__(name)
        except ImportError:
            raise unittest.SkipTest(f"skipped: {name} not installed")

    # Install or patch sys.modules["pytest"] so @pytest.fixture returns plain callable functions under unittest
    mod = sys.modules.get("pytest")
    if mod is None:
        mod = types.ModuleType("pytest")
        sys.modules["pytest"] = mod
    mod.raises = _RaisesCtx
    mod.approx = _Approx
    mod.mark = _Mark()
    mod.fixture = fixture
    mod.importorskip = importorskip
    mod.skip = lambda msg="": (_ for _ in ()).throw(unittest.SkipTest(msg))

    if getattr(unittest.TestLoader, "_pytest_bridged", False):
        return

    def _unwrap_fixture(v):
        """Return (raw_callable, scope) if `v` is a fixture (either our shim or pytest 8.x/9.x FixtureFunctionDefinition)."""
        if getattr(v, "_is_fixture", False) and callable(v):
            return v, getattr(v, "_fixture_scope", "function")
        if hasattr(v, "_get_wrapped_function"):
            marker = getattr(v, "_fixture_function_marker", None)
            return v._get_wrapped_function(), getattr(marker, "scope", "function")
        if hasattr(v, "_fixture_function") and callable(getattr(v, "_fixture_function", None)):
            marker = getattr(v, "_fixture_function_marker", None)
            return v._fixture_function, getattr(marker, "scope", "function")
        if hasattr(v, "_pytestfixturefunction"):
            raw = getattr(v, "__wrapped__", v)
            return raw, getattr(v._pytestfixturefunction, "scope", "function")
        if type(v).__module__.startswith("_pytest"):
            marker = getattr(v, "_fixture_function_marker", getattr(v, "_pytestfixturefunction", None))
            scope = getattr(marker, "scope", "function")
            for cand in getattr(v, "__dict__", {}).values():
                if isinstance(cand, types.FunctionType):
                    return cand, scope
        return None, None

    class _MonkeyPatch:
        def __init__(self):
            self._undo = []

        def setattr(self, target, name, value):
            old = getattr(target, name)
            self._undo.append((target, name, old))
            setattr(target, name, value)

        def setenv(self, name, value):
            old = os.environ.get(name)
            self._undo.append((os.environ, name, old))
            os.environ[name] = str(value)

        def delenv(self, name, raising=True):
            if name not in os.environ and raising:
                raise KeyError(name)
            old = os.environ.get(name)
            self._undo.append((os.environ, name, old))
            os.environ.pop(name, None)

        def undo(self):
            for target, name, old in reversed(self._undo):
                if target is os.environ:
                    if old is None:
                        os.environ.pop(name, None)
                    else:
                        os.environ[name] = old
                else:
                    setattr(target, name, old)

    _orig_load = unittest.TestLoader.loadTestsFromModule

    def _bridged_load(self, module, *args, **kwargs):
        suite = _orig_load(self, module, *args, **kwargs)
        fixtures = {}
        for k, v in vars(module).items():
            raw_fn, scope = _unwrap_fixture(v)
            if raw_fn is not None:
                fixtures[k] = (raw_fn, scope or "function")

        funcs = [
            (k, v) for k, v in vars(module).items()
            if k.startswith("test_")
            and k not in fixtures
            and callable(v)
            and not isinstance(v, type)
            and getattr(v, "__module__", module.__name__) == module.__name__
        ]
        if not funcs:
            return suite

        mod_cache = {}
        mod_stack = contextlib.ExitStack()
        atexit.register(mod_stack.close)

        def resolve_fixture(name, stack):
            if name == "monkeypatch":
                mp = _MonkeyPatch()
                stack.callback(mp.undo)
                return mp
            if name == "tmp_path":
                from pathlib import Path
                return Path(stack.enter_context(tempfile.TemporaryDirectory()))
            if name == "request":
                return types.SimpleNamespace(node=types.SimpleNamespace(name=module.__name__))
            raw_fn, scope = fixtures[name]
            if scope == "module" and name in mod_cache:
                return mod_cache[name]
            t_stack = mod_stack if scope == "module" else stack
            f_args = [resolve_fixture(p, t_stack) for p in inspect.signature(raw_fn).parameters]
            res = raw_fn(*f_args)
            if inspect.isgenerator(res):
                val = next(res)
                t_stack.callback(lambda g=res: next(g, None))
            else:
                val = res
            if scope == "module":
                mod_cache[name] = val
            return val

        runners = []
        for name, fn in funcs:
            params_list = list(getattr(fn, "_parametrize", []))
            for mark in getattr(fn, "pytestmark", ()):
                if getattr(mark, "name", "") == "parametrize":
                    names, vals = mark.args[0], mark.args[1]
                    argnames = [x.strip() for x in names.split(",")] if isinstance(names, str) else list(names)
                    params_list.append((argnames, list(vals)))
            cases = [{}]
            for argnames, vals in reversed(params_list):
                new_cases = []
                for c in cases:
                    for v in vals:
                        row = dict(c)
                        if len(argnames) == 1:
                            row[argnames[0]] = v
                        else:
                            for k, item in zip(argnames, v):
                                row[k] = item
                        new_cases.append(row)
                cases = new_cases
            sig = inspect.signature(fn)
            for case in cases:
                runners.append((name, fn, case, sig))

        total = len(runners)
        ran = [0]
        for name, fn, case, sig in runners:
            def _make_runner(_name=name, _fn=fn, _case=case, _sig=sig):
                def _run():
                    try:
                        with contextlib.ExitStack() as stack:
                            kw = {}
                            for p in _sig.parameters:
                                if p in _case:
                                    kw[p] = _case[p]
                                elif p in fixtures or p in ("monkeypatch", "tmp_path", "request"):
                                    kw[p] = resolve_fixture(p, stack)
                            _fn(**kw)
                    finally:
                        ran[0] += 1
                        if ran[0] >= total:
                            mod_stack.close()
                _run.__name__ = f"{module.__name__}.{_name}"
                return unittest.FunctionTestCase(_run)
            suite.addTest(_make_runner())
        return suite

    unittest.TestLoader.loadTestsFromModule = _bridged_load
    unittest.TestLoader._pytest_bridged = True


_install_unittest_pytest_bridge()
