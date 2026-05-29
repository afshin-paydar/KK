"""Local action execution. Maps validated action types to device capabilities."""

from kk_agent.tts import TTS


class ActionExecutor:
    def __init__(self, tts: TTS):
        self.tts = tts

    def execute(self, action_type: str, params: dict) -> dict:
        """Execute an action locally; return a result dict for the ack."""
        if action_type == "noop":
            return {"ok": True}
        if action_type == "tts.speak":
            self.tts.speak(params.get("text", ""))
            return {"ok": True}
        if action_type == "alert.notify":
            # e.g. blink an LED / log; channels constrained by policy server-side
            return {"ok": True, "notified": params.get("channels", [])}
        if action_type == "gpio.set":
            # TODO: drive GPIO (only if allowed by policy)
            return {"ok": True}
        return {"ok": False, "error": f"unknown action {action_type}"}
