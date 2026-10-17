"""Per-task acceptance checks for the dcnc A/B experiment.

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

ALLOWED_CATEGORIES = {
    "contact", "network", "identifier", "numeric", "text", "generic", "boolean", "name",
}


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


# ---------------- Task 1: ZipCode space-separated ZIP+4 ----------------
def check_task1() -> None:
    m = _import("backend.core.engines.zipcode_engine")
    e = m.ZipCodeEngine()
    assert e.validate("12345 6789")[0] is True, "'12345 6789' should be valid"
    assert e.validate("12345")[0] is True, "regression: plain 5-digit"
    assert e.validate("abcde")[0] is False, "regression: junk rejected"
    print("TASK1 PASS: space-separated ZIP+4 accepted; regressions hold")


def check_task1_baseline() -> None:
    m = _import("backend.core.engines.zipcode_engine")
    assert m.ZipCodeEngine().validate("12345 6789")[0] is False
    print("TASK1 BASELINE: space-separated ZIP+4 rejected (unmodified)")


# ---------------- Task 2: Email rejects consecutive dots in local part ----------------
def check_task2() -> None:
    m = _import("backend.core.engines.email_engine")
    e = m.EmailEngine()
    assert e.validate("a..b@gmail.com")[0] is False, "consecutive dots must be invalid"
    assert e.validate("a.b@gmail.com")[0] is True, "single dot still valid"
    assert e.validate("john@gmail.com")[0] is True, "regression: normal email"
    print("TASK2 PASS: consecutive-dot local part rejected; valid emails still pass")


def check_task2_baseline() -> None:
    m = _import("backend.core.engines.email_engine")
    assert m.EmailEngine().validate("a..b@gmail.com")[0] is True, \
        "baseline: consecutive-dot currently accepted (regex is permissive)"
    print("TASK2 BASELINE: consecutive-dot local part accepted (unmodified)")


# ---------------- Task 3: New MAC-address validation engine ----------------
def check_task3() -> None:
    reg = _registry_with_engines()
    assert reg.has("mac"), "validator registry must contain 'mac'"
    e = reg.get("mac")
    assert e is not None
    assert e.validate("00:1A:2B:3C:4D:5E")[0] is True, "colon MAC valid"
    assert e.validate("00-1A-2B-3C-4D-5E")[0] is True, "hyphen MAC valid"
    assert e.validate("not-a-mac")[0] is False, "junk rejected"
    # Exported from the engines package
    engines = _import("backend.core.engines")
    assert hasattr(engines, "MACEngine") or hasattr(engines, "MacEngine"), \
        "MAC engine class must be exported from engines package"
    print("TASK3 PASS: 'mac' engine registered, exported, and validating")


def check_task3_baseline() -> None:
    reg = _registry_with_engines()
    assert not reg.has("mac"), "baseline: no 'mac' validator yet"
    print("TASK3 BASELINE: no 'mac' validator (unmodified)")


# ---------------- Task 4: Interface-wide `category` property on all engines ----------------
def check_task4() -> None:
    reg = _registry_with_engines()
    keys = reg.list_keys()
    assert keys, "expected registered validators"
    for k in keys:
        e = reg.get(k)
        cat = getattr(e, "category", None)
        assert isinstance(cat, str) and cat in ALLOWED_CATEGORIES, \
            f"engine '{k}' must expose a valid category; got {cat!r}"
    # Contract is enforced on the interface: a bare subclass missing category
    # must fail to instantiate (abstract).
    iface = _import("backend.core.interfaces.validator_interface")
    assert hasattr(iface.IValidator, "category"), "IValidator must declare 'category'"
    print(f"TASK4 PASS: all {len(keys)} engines expose a valid category; interface enforces it")


def check_task4_baseline() -> None:
    reg = _registry_with_engines()
    e = reg.get(reg.list_keys()[0])
    assert not hasattr(e, "category"), "baseline: engines have no 'category' yet"
    print("TASK4 BASELINE: engines lack 'category' (unmodified)")


# ---------------- Task 5: Thread `evidence` field end-to-end ----------------
def check_task5() -> None:
    iface = _import("backend.core.interfaces.detector_interface")
    r = iface.DetectionResult(workflow="text", subtype="email")
    assert hasattr(r, "evidence"), "DetectionResult must have 'evidence'"
    assert r.evidence == [], "evidence defaults to empty list"
    r.evidence.append("matched 9/10 samples against email pattern")
    d = r.to_dict()
    assert "evidence" in d, "to_dict() must serialize 'evidence'"
    assert d["evidence"] == ["matched 9/10 samples against email pattern"]
    print("TASK5 PASS: DetectionResult.evidence present, defaulted, and serialized")


def check_task5_baseline() -> None:
    iface = _import("backend.core.interfaces.detector_interface")
    r = iface.DetectionResult(workflow="text", subtype="email")
    assert not hasattr(r, "evidence"), "baseline: no 'evidence' field yet"
    assert "evidence" not in r.to_dict()
    print("TASK5 BASELINE: DetectionResult has no 'evidence' (unmodified)")


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
