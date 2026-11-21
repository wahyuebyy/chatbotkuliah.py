"""LLM tiruan untuk menguji alur tanpa API key / internet."""
from types import SimpleNamespace


class FakeMessages:
    def __init__(self, balasan=None, error=None):
        self.balasan, self.error, self.panggilan = balasan, error, []

    def create(self, **kwargs):
        self.panggilan.append(kwargs)
        if self.error:
            raise self.error
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.balasan)])


class FakeClient:
    def __init__(self, balasan=None, error=None):
        self.messages = FakeMessages(balasan, error)
