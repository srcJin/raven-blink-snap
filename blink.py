"""Time-based double tracking-loss detector, independent of Qt and the SDK."""
from dataclasses import dataclass


@dataclass
class BlinkDetector:
    minimum_loss: float = 0.07
    maximum_loss: float = 0.35
    maximum_gap: float = 0.65
    minimum_recovery: float = 0.05
    cooldown: float = 2.0
    loss_started: float | None = None
    recovered_at: float | None = None
    first_blink: float | None = None
    cooldown_until: float = 0.0
    last_sample: float | None = None

    def reset(self):
        self.loss_started = None
        self.recovered_at = None
        self.first_blink = None
        self.last_sample = None

    def sample(self, tracked: bool, now: float) -> bool:
        # A stalled sensor/poll loop must never be interpreted as a blink.
        if self.last_sample is not None and (now < self.last_sample or now - self.last_sample > 0.15):
            self.reset()
        self.last_sample = now
        if now < self.cooldown_until:
            self.loss_started = None
            self.first_blink = None
            self.recovered_at = now if tracked else None
            return False
        if self.first_blink is not None and now - self.first_blink > self.maximum_gap + self.maximum_loss:
            self.first_blink = None
        if not tracked:
            if self.loss_started is None:
                if self.recovered_at is None or now - self.recovered_at < self.minimum_recovery:
                    self.first_blink = None
                    self.recovered_at = None
                    return False
                self.loss_started = now
            return False
        if self.loss_started is None:
            if self.recovered_at is None:
                self.recovered_at = now
            return False
        duration = now - self.loss_started
        started = self.loss_started
        self.loss_started = None
        self.recovered_at = now
        if not self.minimum_loss <= duration <= self.maximum_loss:
            self.first_blink = None
            return False
        if self.first_blink is not None and started - self.first_blink <= self.maximum_gap:
            self.first_blink = None
            self.cooldown_until = now + self.cooldown
            return True
        self.first_blink = now
        return False
