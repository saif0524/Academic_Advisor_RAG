"""LLM seam configuration (agent/llm/config): provider factory + stubs.

Tests stay offline: the ollama provider construction must not perform I/O;
network calls only happen at invoke time in real runtime use. The
degrade-to-rules fallback paths are tested with fake model objects."""
import pytest

from agent.llm.config import LLMConfig, get_classifier, get_llm, get_summarizer
from agent.llm.classify import LLMClassifier, StubClassifier
from agent.llm.summarize import LLMSummarizer, StubSummarizer


def test_default_config_targets_local_ollama_glm_flash():
    config = LLMConfig.from_env({"ADVISOR_LLM_PROVIDER": "ollama"})
    assert config.provider == "ollama"
    assert config.model == "glm-5.3-flash:cloud"
    assert config.base_url == "http://localhost:11434"


def test_env_overrides_model_and_base_url():
    config = LLMConfig.from_env({
        "ADVISOR_LLM_PROVIDER": "ollama",
        "ADVISOR_LLM_MODEL": "qwen3.5:latest",
        "ADVISOR_LLM_BASE_URL": "http://127.0.0.1:11434",
    })
    assert config.model == "qwen3.5:latest"
    assert config.base_url == "http://127.0.0.1:11434"


def test_stub_provider_needs_no_model():
    config = LLMConfig.from_env({"ADVISOR_LLM_PROVIDER": "stub"})
    assert get_llm(config) is None  # the deterministic stub path constructs no model


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError):
        LLMConfig.from_env({"ADVISOR_LLM_PROVIDER": "warp-drive"})


def test_stub_wiring_returns_deterministic_components():
    config = LLMConfig.from_env({"ADVISOR_LLM_PROVIDER": "stub"})
    assert isinstance(get_classifier(config), StubClassifier)
    assert isinstance(get_summarizer(config), StubSummarizer)
    assert get_llm(config) is None  # no model object needed offline


def test_ollama_wiring_builds_chat_model_without_io():
    config = LLMConfig.from_env({
        "ADVISOR_LLM_PROVIDER": "ollama", "ADVISOR_LLM_MODEL": "qwen3.5:latest"})
    model = get_llm(config)
    assert type(model).__name__ == "ChatOllama"
    assert isinstance(get_classifier(config), LLMClassifier)
    assert isinstance(get_summarizer(config), LLMSummarizer)


# ------------------------------------------------- degrade-to-rules fallbacks

class _Raw:
    def __init__(self, intent="exact", params=None, clarification_question=None):
        self.intent = intent
        self.params = params or {}
        self.clarification_question = clarification_question


class _FakeStructuredModel:
    """Mimics ChatOllama's with_structured_output seam (no network)."""

    def __init__(self, raw=None, raise_on_invoke=False):
        self._raw = raw or _Raw()
        self._raise = raise_on_invoke

    def with_structured_output(self, schema, method=None):
        assert method == "json_schema", "the ollama path must enforce JSON"

        result = self

        class _Callable:
            def invoke(self, _messages):
                if result._raise:
                    raise RuntimeError("model exploded")
                return result._raw

        return _Callable()

    def invoke(self, _messages):  # summarizer seam
        raise RuntimeError("model down")


def test_llm_classifier_normalizes_freeform_params():
    """A model returning course_id (not course_mentions) still routes."""
    classifier = LLMClassifier(_FakeStructuredModel(_Raw("exact", {"course_id": "CSE 3330"})))
    result = classifier.classify("What time does CSE 3330 meet?")
    assert result.intent == "exact"
    assert result.params["course_mentions"] == ["3330"]


def test_llm_classifier_fills_course_id_for_actions():
    result = LLMClassifier(_FakeStructuredModel()) \
        .classify("add CSE 4308 to my classes")  # raw intent 'exact' → hmm
    # intent 'exact' with 'add' phrasing: params carry the mention — the
    # graph routes exact; an actual action needs intent propose_action
    assert result.params["course_mentions"] == ["4308"]


def test_llm_classifier_degrades_to_rules_on_unknown_intent():
    classifier = LLMClassifier(_FakeStructuredModel(_Raw("purchase", {})))
    result = classifier.classify("Add CSE 4308 to my classes")
    assert result.intent == "propose_action"
    assert result.params["action_type"] == "add_class"
    assert result.params["course_id"] == "4308"


def test_llm_classifier_degrades_to_rules_on_model_failure():
    classifier = LLMClassifier(_FakeStructuredModel(raise_on_invoke=True))
    result = classifier.classify("Can I take CSE 1311?")
    assert result.intent == "audit"
    assert result.params.get("course_mentions") == ["1311"]


def test_llm_summarizer_degrades_to_deterministic_rendering():
    failing = _FakeStructuredModel(raise_on_invoke=True)
    summarizer = LLMSummarizer(failing)
    payload = {"course": {"course_id": "1320", "title": "INTERMEDIATE PROGRAMMING",
                          "credit_hours": 3, "description": None},
               "result": {"eligible": False, "checks": []}}
    reply = summarizer.summarize("audit", payload)
    assert "1320" in reply  # deterministic payload rendering, still grounded


def test_summarizer_reads_both_message_text_shapes():
    """BaseMessage.text is a method in some langchain-core versions and a
    property in others — the summarizer must read whatever arrives."""
    from agent.llm.summarize import LLMSummarizer

    class MethodShape:  # text is callable
        def text(self):
            return "method-shaped answer"

    class ContentShape:  # no .text — content string
        content = "content-shaped answer"

    method_model = type("M", (), {"invoke": staticmethod(lambda _msgs: MethodShape())})()
    content_model = type("M", (), {"invoke": staticmethod(lambda _msgs: ContentShape())})()
    assert LLMSummarizer(method_model).summarize("audit", {}) == "method-shaped answer"
    assert LLMSummarizer(content_model).summarize("audit", {}) == "content-shaped answer"