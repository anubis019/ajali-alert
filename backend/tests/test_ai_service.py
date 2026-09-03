from ai_service import MockAIProvider, OpenAIProvider, get_ai_provider


def test_chat_uses_context_when_status_is_asked():
    provider = MockAIProvider()
    reply = provider.chat(
        "what is the status of this incident?",
        incident_id="inc-123",
        context={"status": "DISPATCHING", "priority": 4},
        user_role="dispatcher",
    )
    assert "DISPATCHING" in reply.upper()


def test_chat_offers_safe_direction_for_emergency_questions():
    provider = MockAIProvider()
    reply = provider.chat("what should i do if there is a fire?", user_role="citizen")
    assert "call" in reply.lower() or "evacuate" in reply.lower() or "emergency" in reply.lower()


def test_chat_summarizes_incident_context_for_dispatchers():
    provider = MockAIProvider()
    reply = provider.chat(
        "summarize this case",
        incident_id="inc-456",
        context={
            "status": "DISPATCHING",
            "priority": 5,
            "type": "medical",
            "location": "Kisumu Road",
            "description": "multiple injuries after an accident",
        },
        user_role="dispatcher",
    )
    assert "medical" in reply.lower()
    assert "kisumu road" in reply.lower()


def test_provider_selection_uses_mock_without_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert isinstance(get_ai_provider(), MockAIProvider)


def test_provider_selection_uses_openai_when_key_exists(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    provider = get_ai_provider()
    assert isinstance(provider, OpenAIProvider)
