"""On-device text-to-speech. Runs locally (e.g. Piper); audio stays on the Pi."""


class TTS:
    def __init__(self, model_path: str | None = None):
        self.model_path = model_path
        # TODO: load Piper voice model here.

    def speak(self, text: str) -> None:
        """Synthesize and play `text` on the local audio device."""
        # TODO: piper synth -> aplay. Placeholder for dev:
        print(f"[tts] {text}")
