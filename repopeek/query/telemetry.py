"""Session-rollup telemetry for the RepoPeek MCP server.

Accumulates per-session usage and *estimated* context savings across MCP tool
calls. The savings number is an estimate, not a measurement: the MCP server
cannot observe the host agent's prompt boundaries or the file reads it avoided,
so savings are modeled from the compiler's own `raw_file_tokens` baseline
(tokens an agent would spend reading the full affected files) minus the tokens
RepoPeek actually returned.

Design constraints (per AGENTS.md Ponytail ladder):
- Zero-dependency core: counters are plain Python and always work.
- OpenTelemetry is optional. If `opentelemetry` is not installed, or export is
  not configured, the accumulator still functions and the summary still renders.
- No network egress by default. OTLP export is opt-in via REPOPEEK_OTEL_ENDPOINT.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# Average source-file token assumption, mirrored from
# ContextCompiler._estimate_raw_file_tokens so pack-call baselines stay consistent
# with the compiler's own estimate when a per-file breakdown is unavailable.
_AVG_FILE_TOKENS = 1200


@dataclass
class ToolStat:
    """Per-tool aggregate counters."""
    calls: int = 0
    total_latency_ms: float = 0.0
    tokens_returned: int = 0

    def record(self, latency_ms: float, tokens_returned: int) -> None:
        self.calls += 1
        self.total_latency_ms += latency_ms
        self.tokens_returned += tokens_returned

    @property
    def avg_latency_ms(self) -> float:
        return round(self.total_latency_ms / self.calls, 2) if self.calls else 0.0


class TelemetrySession:
    """Accumulates MCP tool usage and estimated savings for one server session.

    The server process lives for the duration of an agent session, so a single
    long-lived instance of this class is the session rollup (Option A). No
    per-prompt boundary detection is attempted; that would require agent-side
    cooperation and is intentionally out of scope.
    """

    def __init__(self, exporter: Optional["OtelExporter"] = None) -> None:
        self.started_at = time.time()
        self.total_calls = 0
        self.tokens_returned = 0
        self.tokens_saved_estimate = 0
        self.files_avoided_estimate = 0
        self.per_tool: Dict[str, ToolStat] = {}
        self._exporter = exporter

    def record_call(
        self,
        tool_name: str,
        latency_ms: float,
        tokens_returned: int,
        tokens_saved_estimate: int = 0,
        files_avoided_estimate: int = 0,
    ) -> None:
        """Record a single completed tool call.

        Args:
            tool_name: MCP tool name (e.g. "repopeek_context").
            latency_ms: Wall-clock duration of the tool dispatch.
            tokens_returned: Estimated tokens of the payload RepoPeek returned.
            tokens_saved_estimate: Estimated tokens the agent avoided reading.
                Only context/pack tools contribute a non-zero value.
            files_avoided_estimate: Count of files the agent did not have to open.
        """
        self.total_calls += 1
        self.tokens_returned += max(0, tokens_returned)
        self.tokens_saved_estimate += max(0, tokens_saved_estimate)
        self.files_avoided_estimate += max(0, files_avoided_estimate)

        stat = self.per_tool.get(tool_name)
        if stat is None:
            stat = ToolStat()
            self.per_tool[tool_name] = stat
        stat.record(latency_ms, max(0, tokens_returned))

        if self._exporter is not None:
            self._exporter.export_call(
                tool_name=tool_name,
                latency_ms=latency_ms,
                tokens_returned=max(0, tokens_returned),
                tokens_saved_estimate=max(0, tokens_saved_estimate),
                files_avoided_estimate=max(0, files_avoided_estimate),
            )

    @property
    def reduction_pct(self) -> float:
        """Estimated percentage reduction vs the modeled raw-read baseline."""
        baseline = self.tokens_returned + self.tokens_saved_estimate
        if baseline <= 0:
            return 0.0
        return round(100.0 * self.tokens_saved_estimate / baseline, 1)

    def to_dict(self) -> Dict[str, Any]:
        """Serializable session rollup."""
        return {
            "session_uptime_sec": round(time.time() - self.started_at, 1),
            "total_tool_calls": self.total_calls,
            "tokens_returned": self.tokens_returned,
            "tokens_saved_estimate": self.tokens_saved_estimate,
            "files_avoided_estimate": self.files_avoided_estimate,
            "estimated_reduction_pct": self.reduction_pct,
            "note": (
                "Savings are an ESTIMATE. Baseline = tokens an agent would read "
                "opening the full affected files (RepoPeek compiler's raw_file_tokens); "
                "actual = tokens RepoPeek returned. The MCP server cannot measure the "
                "host agent's real token spend."
            ),
            "per_tool": {
                name: {
                    "calls": s.calls,
                    "tokens_returned": s.tokens_returned,
                    "avg_latency_ms": s.avg_latency_ms,
                }
                for name, s in sorted(self.per_tool.items())
            },
        }

    def summary_line(self) -> str:
        """One-line human-readable rollup."""
        return (
            f"RepoPeek this session: {self.total_calls} tool calls "
            f"· ~{self.tokens_returned} tokens returned "
            f"· est. ~{self.tokens_saved_estimate} tokens / "
            f"~{self.files_avoided_estimate} file reads avoided "
            f"(est. {self.reduction_pct}% reduction)."
        )

    @staticmethod
    def estimate_pack_baseline_tokens(affected_files_count: int) -> int:
        """Model a baseline for context_pack calls that lack raw_file_tokens.

        Mirrors the compiler's average-file assumption so pack and context
        savings use a consistent model.
        """
        return max(0, affected_files_count) * _AVG_FILE_TOKENS


class OtelExporter:
    """Optional OpenTelemetry metrics exporter.

    Instantiated only when OpenTelemetry is importable. Falls back silently to a
    no-op if the SDK is missing so the zero-dependency path is never broken.
    """

    def __init__(self) -> None:
        self._enabled = False
        self._counters: Dict[str, Any] = {}
        try:
            self._init_otel()
            self._enabled = True
        except Exception:
            # Any failure (missing SDK, bad endpoint) degrades to no-op.
            self._enabled = False

    def _init_otel(self) -> None:
        from opentelemetry import metrics
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import (
            ConsoleMetricExporter,
            PeriodicExportingMetricReader,
        )

        endpoint = os.environ.get("REPOPEEK_OTEL_ENDPOINT", "").strip()
        if endpoint:
            # OTLP export is opt-in. Import lazily so the OTLP extra is only
            # required when an endpoint is actually configured.
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
                OTLPMetricExporter,
            )
            exporter: Any = OTLPMetricExporter(endpoint=endpoint)
        else:
            # Default: local console export, no network egress.
            exporter = ConsoleMetricExporter()

        reader = PeriodicExportingMetricReader(exporter)
        provider = MeterProvider(metric_readers=[reader])
        metrics.set_meter_provider(provider)
        meter = metrics.get_meter("repopeek.mcp")

        self._counters["calls"] = meter.create_counter("repopeek.tool.calls")
        self._counters["tokens_returned"] = meter.create_counter(
            "repopeek.pack.tokens_returned"
        )
        self._counters["tokens_saved"] = meter.create_counter(
            "repopeek.tokens_saved_estimate"
        )
        self._counters["files_avoided"] = meter.create_counter(
            "repopeek.files_avoided_estimate"
        )
        self._latency = meter.create_histogram("repopeek.tool.latency_ms")

    def export_call(
        self,
        tool_name: str,
        latency_ms: float,
        tokens_returned: int,
        tokens_saved_estimate: int,
        files_avoided_estimate: int,
    ) -> None:
        if not self._enabled:
            return
        try:
            attrs = {"tool": tool_name}
            self._counters["calls"].add(1, attrs)
            self._counters["tokens_returned"].add(tokens_returned, attrs)
            self._counters["tokens_saved"].add(tokens_saved_estimate, attrs)
            self._counters["files_avoided"].add(files_avoided_estimate, attrs)
            self._latency.record(latency_ms, attrs)
        except Exception:
            # Never let telemetry export break a tool call.
            pass


def build_session() -> TelemetrySession:
    """Construct a TelemetrySession, enabling OTel export only when opted in.

    OTel export is attempted when REPOPEEK_OTEL=1 (console) or when
    REPOPEEK_OTEL_ENDPOINT is set (OTLP). Otherwise the pure-Python accumulator
    is used, which still powers the session summary.
    """
    want_otel = (
        os.environ.get("REPOPEEK_OTEL", "").strip() in ("1", "true", "True")
        or bool(os.environ.get("REPOPEEK_OTEL_ENDPOINT", "").strip())
    )
    exporter: Optional[OtelExporter] = None
    if want_otel:
        exporter = OtelExporter()
        if not exporter._enabled:
            # Telemetry requested but SDK unavailable: tell the operator once,
            # on stderr, then continue with the pure-Python path.
            print(
                "[repopeek] OpenTelemetry export requested but unavailable; "
                "install 'repopeek[telemetry]'. Continuing with local counters.",
                file=sys.stderr,
            )
            exporter = None
    return TelemetrySession(exporter=exporter)
