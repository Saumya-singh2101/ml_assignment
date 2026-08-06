import time
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class InstrumentationTimer:
    started_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc
        )
    )

    capture_start: float | None = None
    capture_end: float | None = None

    dispatch_start: float | None = None
    dispatch_end: float | None = None

    provider_start: float | None = None
    first_byte: float | None = None
    first_token: float | None = None
    last_token: float | None = None

    render_end: float | None = None

    def now(self) -> float:
        return time.perf_counter()

    def start_capture(self):
        self.capture_start = self.now()

    def end_capture(self):
        self.capture_end = self.now()

    def start_dispatch(self):
        self.dispatch_start = self.now()

    def end_dispatch(self):
        self.dispatch_end = self.now()

    def start_provider(self):
        self.provider_start = self.now()

    def mark_first_byte(self):
        if self.first_byte is None:
            self.first_byte = self.now()

    def mark_first_token(self):
        if self.first_token is None:
            self.first_token = self.now()

    def mark_last_token(self):
        self.last_token = self.now()

    def mark_render_complete(self):
        self.render_end = self.now()

    @staticmethod
    def elapsed(
        start: float | None,
        end: float | None,
    ) -> float:
        if start is None or end is None:
            return 0.0

        return round(
            (end - start) * 1000,
            3,
        )

    def latency(self) -> dict[str, float]:
        e2e_end = (
            self.render_end
            or self.last_token
        )

        return {
            "t_capture": self.elapsed(
                self.capture_start,
                self.capture_end,
            ),
            "t_dispatch": self.elapsed(
                self.dispatch_start,
                self.dispatch_end,
            ),
            "ttfb": self.elapsed(
                self.provider_start,
                self.first_byte,
            ),
            "ttft": self.elapsed(
                self.provider_start,
                self.first_token,
            ),
            "t_stream": self.elapsed(
                self.first_token,
                self.last_token,
            ),
            "t_render": self.elapsed(
                self.last_token,
                self.render_end,
            ),
            "e2e": self.elapsed(
                self.capture_start,
                e2e_end,
            ),
        }