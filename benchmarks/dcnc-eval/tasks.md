# dcnc A/B Task Set (5 New Problems, Frozen Before Evaluation)

Target repo: `testing/dcnc` (Data Anomaly Detector & Correction Tool, Python).
Each task is run twice - Arm 1 (file-first) and Arm 2 (RepoPeek-first) - on an
identical clean baseline. Acceptance is enforced by `acceptance.py <id>`
(post-change) and `<id>-baseline` (clean state). Tasks are ordered by blast
radius (leaf -> architectural).

| # | Difficulty | Change | Files touched (expected) | Blast radius |
|---|---|---|---|---|
| 1 | Trivial (leaf) | SSN engine accepts space-separated format (`123 45 6789`) | `engines/ssn_engine.py` | none (leaf) |
| 2 | Localized | URL engine rejects bare numeric/IP address host (`http://192.168.1.1`) | `engines/url_engine.py` | url consumed by detection/clustering |
| 3 | Cross-module feature | Add new `credit_card` validation engine + register + export | `engines/credit_card_engine.py` (new), `engines/__init__.py` | registry + detection pick-up |
| 4 | Interface-wide | Add abstract `get_supported_mime_types` method to `IValidator`, implement across all engines | `interfaces/validator_interface.py` + all `engines/*_engine.py` | all validator implementors |
| 5 | Architectural / data-flow | Thread new `risk_tier: str` field through `DetectionResult` -> detector -> correction output writer | `interfaces/detector_interface.py`, detector(s), `correction/output_writer.py` | detection -> interfaces -> correction/output |

## Task 1 - Trivial (leaf change)
Accept a space between digit groups in `SSNEngine` (`123 45 6789`).
- Add pattern `^\d{3}\s\d{2}\s\d{4}$` and strip spaces in `_validate_normalized`.
- DoD: `acceptance.py 1` passes (`validate("123 45 6789") == (True, ...)`), regressions hold.

## Task 2 - Localized (one method, real semantics)
Tighten `URLEngine` to reject bare numeric/IP address hosts.
- In `_validate_normalized`, check domain components; reject if host is pure IP or numeric TLD.
- DoD: `acceptance.py 2` passes (`http://192.168.1.1/api` invalid; `https://example.com/api` and `http://sub.domain.org` valid).

## Task 3 - Cross-module feature (new plugin)
Add a credit card validator following the engine plugin pattern.
- New `engines/credit_card_engine.py`: `@register_validator("credit_card")`, card length/pattern check, Luhn algorithm checksum.
- Export `CreditCardEngine` from `engines/__init__.py`.
- DoD: `acceptance.py 3` passes (registry has `credit_card`; valid card passes; invalid Luhn fails; class exported).

## Task 4 - Interface-wide (fan-out across all engines)
Add abstract `get_supported_mime_types(self) -> List[str]` method to `IValidator` and implement on every engine.
- `validator_interface.py`: declare abstract `get_supported_mime_types`.
- Each `engines/*_engine.py` (zipcode, email, uuid, phone, url, ip_address, name, boolean, ssn, generic_string, generic_numeric): implement and return `["text/plain"]` (or specific MIME list).
- DoD: `acceptance.py 4` passes (every registered validator returns valid non-empty list of MIME strings; interface declares it).

## Task 5 - Architectural / data-flow (cross-layer field)
Thread a new `risk_tier: str` field end-to-end so anomaly severity rating reaches the correction report.
- `detector_interface.py`: add `risk_tier: str = "low"` to `DetectionResult`; include it in `to_dict()`.
- Populate or maintain it in `backend/core/detection/workflow_detector.py` and write it in `backend/core/correction/output_writer.py`.
- DoD: `acceptance.py 5` passes (field present, defaults to `"low"`, serialized in `to_dict()`). Full-pipeline propagation verified by inspection.

## Revert protocol
Between arms, restore the clean baseline with dcnc's own git:
`git -C testing/dcnc checkout -- .` and remove any new untracked files (e.g. `credit_card_engine.py`).
Confirm with `acceptance.py <id>-baseline` for all five.
