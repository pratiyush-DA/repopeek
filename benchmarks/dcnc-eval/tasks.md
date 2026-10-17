# dcnc A/B Task Set (FROZEN before either arm)

Target repo: `testing/dcnc` (Data Anomaly Detector & Correction Tool, Python).
Each task is run twice — Arm 1 (file-first) and Arm 2 (RepoPeek-first) — on an
identical clean baseline. Acceptance is enforced by `acceptance.py <id>`
(post-change) and `<id>-baseline` (clean state). Tasks are ordered by blast
radius (easy → architectural).

| # | Difficulty | Change | Files touched (expected) | Blast radius |
|---|-----------|--------|--------------------------|--------------|
| 1 | Trivial | ZIP engine accepts space-separated ZIP+4 (`12345 6789`) | `engines/zipcode_engine.py` | none (leaf) |
| 2 | Localized | Email engine rejects consecutive dots in local part (`a..b@x.com`) | `engines/email_engine.py` | email is consumed by detection/clustering |
| 3 | Cross-module feature | Add a new `mac` validation engine + register + export | `engines/mac_engine.py` (new), `engines/__init__.py` | registry + detection pick-up |
| 4 | Interface-wide | Add abstract `category` property to `IValidator`, implement on all engines | `interfaces/validator_interface.py` + every `engines/*_engine.py` | all validator implementors |
| 5 | Architectural / data-flow | Thread new `evidence: list[str]` field through `DetectionResult` → detector → correction report | `interfaces/detector_interface.py`, detector(s), `correction/output_writer.py` | detection → interfaces → correction/output |

## Task 1 — Trivial (leaf change)
Accept a space between the 5-digit prefix and the +4 suffix in `ZipCodeEngine`.
- Add pattern `^\d{5}\s\d{4}$` and accept it in `_validate_normalized`.
- DoD: `acceptance.py 1` passes (`validate("12345 6789") == (True, ...)`), 5-digit and junk regressions hold.

## Task 2 — Localized (one method, real semantics)
Tighten `EmailEngine` to reject consecutive dots in the local part.
- In `_validate_normalized`, reject when `local` contains `".."`.
- DoD: `acceptance.py 2` passes (`a..b@gmail.com` invalid; `a.b@gmail.com` and `john@gmail.com` valid).

## Task 3 — Cross-module feature (new plugin)
Add a MAC-address validator following the engine plugin pattern.
- New `engines/mac_engine.py`: `@register_validator("mac")`, patterns for colon and hyphen forms, `_validate_normalized`.
- Export the class from `engines/__init__.py` (`__all__`).
- DoD: `acceptance.py 3` passes (registry has `mac`; colon/hyphen MACs valid; class exported).

## Task 4 — Interface-wide (fan-out across all engines)
Add an abstract `category` property to the `IValidator` interface and implement a
coarse category on every engine (allowed: contact, network, identifier, numeric,
text, generic, boolean, name).
- `validator_interface.py`: declare abstract `category`.
- Each `engines/*_engine.py` (zipcode, email, uuid, phone, url, ip_address, name, boolean, ssn, generic_string, generic_numeric): return a category.
- DoD: `acceptance.py 4` passes (every registered validator returns a valid category; interface declares it).

## Task 5 — Architectural / data-flow (cross-layer field)
Thread a new `evidence: list[str]` field end-to-end so detection rationale reaches
the correction report.
- `detector_interface.py`: add `evidence: List[str] = field(default_factory=list)` to `DetectionResult`; include it in `to_dict()`.
- Populate it where detection results are built (detector/pattern analyzer) and surface it in `correction/output_writer.py` report output.
- DoD: `acceptance.py 5` passes (field present, defaults to `[]`, serialized in `to_dict()`). Full-pipeline propagation verified by inspection where unit assertion is impractical.

## Revert protocol
Between arms, restore the clean baseline with dcnc's own git:
`git -C testing/dcnc checkout -- .` and remove any new untracked files (e.g. `mac_engine.py`).
Confirm with `acceptance.py <id>-baseline` for all five.
