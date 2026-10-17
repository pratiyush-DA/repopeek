"""Per-task acceptance checks for the dcnc A/B experiment (5 New Tasks).

Each check is a deterministic assertion that proves a task's required behavior.
Run with the eval venv and PYTHONPATH pointed at the dcnc repo:

    $env:PYTHONPATH="testing/dcnc"; .venv\\Scripts\\python benchmarks/dcnc-eval/acceptance.py <task_id>

task_id in {1,2,3,4,5} (post-change DoD) or <n>-baseline (pre-change state).
Exit 0 = pass, non-zero = fail. The '-baseline' variants assert the repo is in
its ORIGINAL state, so they confirm a clean revert between arms.
"""
from __future__ import annotations

import importlib
import sys


def _reset_backend() -> None:
    """Drop cached dcnc modules so edits + fresh registry are picked up."""
    for name in list(sys.modules):
        if name == "backend" or name.startswith("backend."):
            sys.modules.pop(name, None)


def _import(modpath: str):
    _reset_backend()
    return importlib.import_module(modpath)


def _registry_with_engines():
    """Import engines (runs @register_validator) and return the validator registry."""
    _reset_backend()
    importlib.import_module("backend.core.engines")  # triggers registration
    reg = importlib.import_module("backend.core.registry")
    return reg.get_validator_registry()


# ---------------- Task 1: SSN space-separated format ----------------
def check_task1() -> None:
    m = _import("backend.core.engines.ssn_engine")
    e = m.SSNEngine()
    assert e.validate("123 45 6789")[0] is True, "'123 45 6789' should be valid"
    assert e.validate("123-45-6789")[0] is True, "regression: hyphen format"
    assert e.validate("123456789")[0] is True, "regression: plain 9-digit"
    assert e.validate("000-45-6789")[0] is False, "regression: invalid area 000"
    assert e.validate("abcdefghi")[0] is False, "regression: letters rejected"
    print("TASK1 PASS: space-separated SSN accepted; regressions hold")


def check_task1_baseline() -> None:
    m = _import("backend.core.engines.ssn_engine")
    assert m.SSNEngine().validate("123 45 6789")[0] is False
    print("TASK1 BASELINE: space-separated SSN rejected (unmodified)")


# ---------------- Task 2: URL reject bare numeric/IP address host ----------------
def check_task2() -> None:
    m = _import("backend.core.engines.url_engine")
    e = m.URLEngine()
    assert e.validate("http://192.168.1.1/api")[0] is False, "bare IP host in URL must be rejected"
    assert e.validate("https://10.0.0.1")[0] is False, "bare private IP in URL must be rejected"
    assert e.validate("https://example.com/api")[0] is True, "standard domain URL still valid"
    assert e.validate("http://sub.domain.org/path")[0] is True, "subdomain URL still valid"
    print("TASK2 PASS: bare numeric IP hosts in URL rejected; domain URLs still pass")


def check_task2_baseline() -> None:
    m = _import("backend.core.engines.url_engine")
    assert m.URLEngine().validate("http://192.168.1.1/api")[0] is True, \
        "baseline: bare IP host currently accepted"
    print("TASK2 BASELINE: bare numeric IP host accepted (unmodified)")


# ---------------- Task 3: New CreditCard validation engine ----------------
def check_task3() -> None:
    reg = _registry_with_engines()
    assert reg.has("credit_card"), "validator registry must contain 'credit_card'"
    e = reg.get("credit_card")
    assert e is not None
    assert e.validate("4532015112830366")[0] is True, "valid Visa credit card passes"
    assert e.validate("4532-0151-1283-0366")[0] is True, "formatted card number passes"
    assert e.validate("4532015112830367")[0] is False, "invalid Luhn checksum rejected"
    assert e.validate("not-a-card")[0] is False, "junk rejected"
    engines = _import("backend.core.engines")
    assert hasattr(engines, "CreditCardEngine"), "CreditCardEngine must be exported from engines"
    print("TASK3 PASS: 'credit_card' engine registered, exported, and validating")


def check_task3_baseline() -> None:
    reg = _registry_with_engines()
    assert not reg.has("credit_card"), "baseline: no 'credit_card' validator yet"
    print("TASK3 BASELINE: no 'credit_card' validator (unmodified)")


# ---------------- Task 4: Interface-wide get_supported_mime_types on all engines ----------------
def check_task4() -> None:
    reg = _registry_with_engines()
    keys = reg.list_keys()
    assert keys, "expected registered validators"
    for k in keys:
        e = reg.get(k)
        mimes = getattr(e, "get_supported_mime_types", None)
        assert callable(mimes), f"engine '{k}' must implement get_supported_mime_types()"
        res = e.get_supported_mime_types()
        assert isinstance(res, list) and len(res) > 0 and all(isinstance(x, str) for x in res), \
            f"engine '{k}' must return non-empty list of mime strings; got {res!r}"
    iface = _import("backend.core.interfaces.validator_interface")
    assert hasattr(iface.IValidator, "get_supported_mime_types"), \
        "IValidator must declare 'get_supported_mime_types'"
    print(f"TASK4 PASS: all {len(keys)} engines expose get_supported_mime_types(); interface enforces it")


def check_task4_baseline() -> None:
    reg = _registry_with_engines()
    e = reg.get(reg.list_keys()[0])
    assert not hasattr(e, "get_supported_mime_types"), "baseline: engines lack 'get_supported_mime_types'"
    print("TASK4 BASELINE: engines lack 'get_supported_mime_types' (unmodified)")


# ---------------- Task 5: Thread risk_tier field end-to-end ----------------
def check_task5() -> None:
    iface = _import("backend.core.interfaces.detector_interface")
    r = iface.DetectionResult(workflow="text", subtype="email")
    assert hasattr(r, "risk_tier"), "DetectionResult must have 'risk_tier'"
    assert r.risk_tier == "low", "risk_tier defaults to 'low'"
    r.risk_tier = "high"
    d = r.to_dict()
    assert "risk_tier" in d, "to_dict() must serialize 'risk_tier'"
    assert d["risk_tier"] == "high"
    print("TASK5 PASS: DetectionResult.risk_tier present, defaulted, and serialized")


def check_task5_baseline() -> None:
    iface = _import("backend.core.interfaces.detector_interface")
    r = iface.DetectionResult(workflow="text", subtype="email")
    assert not hasattr(r, "risk_tier"), "baseline: no 'risk_tier' field yet"
    assert "risk_tier" not in r.to_dict()
    print("TASK5 BASELINE: DetectionResult has no 'risk_tier' (unmodified)")


TABLE = {
    "1": check_task1, "1-baseline": check_task1_baseline,
    "2": check_task2, "2-baseline": check_task2_baseline,
    "3": check_task3, "3-baseline": check_task3_baseline,
    "4": check_task4, "4-baseline": check_task4_baseline,
    "5": check_task5, "5-baseline": check_task5_baseline,
}


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    tid = argv[0]
    fn = TABLE.get(tid)
    if fn is None:
        print(f"unknown task id: {tid}; available: {sorted(TABLE)}")
        return 2
    try:
        fn()
        return 0
    except AssertionError as e:
        print(f"FAIL [{tid}]: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
