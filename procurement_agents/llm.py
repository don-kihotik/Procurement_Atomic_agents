"""Фабрика LLM-провайдера. Одна переменная LLM_PROVIDER переключает фазу.

Возвращает (client, model, mode):
  mode == "anthropic" -> instructor-патченый Anthropic-клиент (system отдельным аргументом)
  mode == "openai"    -> instructor-патченый OpenAI-клиент (Ollama / Yandex, JSON-режим)
  mode == "stub"      -> без LLM (детерминированная заглушка в агенте)
"""
from __future__ import annotations

import os


def get_client_and_model():
    provider = os.getenv("LLM_PROVIDER", "stub").lower()

    if provider == "stub":
        return None, None, "stub"

    if provider == "claude":
        import instructor
        import anthropic
        client = instructor.from_anthropic(anthropic.Anthropic())
        model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
        return client, model, "anthropic"

    if provider == "local":
        import instructor
        import openai
        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        client = instructor.from_openai(
            openai.OpenAI(base_url=base, api_key="ollama"),
            mode=instructor.Mode.JSON,
        )
        model = os.getenv("OLLAMA_MODEL", "gemma4")
        return client, model, "openai"

    if provider == "yandex":
        import instructor
        import openai
        base = os.getenv("YANDEX_BASE_URL", "https://llm.api.cloud.yandex.net/v1")
        folder = os.getenv("YANDEX_FOLDER_ID", "")
        client = instructor.from_openai(
            openai.OpenAI(base_url=base, api_key=os.getenv("YANDEX_API_KEY", "")),
            mode=instructor.Mode.JSON,
        )
        # Яндекс ждёт идентификатор модели вида gpt://<folder>/<model>
        model = f"gpt://{folder}/{os.getenv('YANDEX_MODEL', 'yandexgpt/latest')}"
        return client, model, "openai"

    raise ValueError(f"неизвестный LLM_PROVIDER='{provider}' (local|stub|claude|yandex)")


def structured_complete(client, model, mode, *, system: str, user: str, response_model, max_tokens: int = 2000):
    """Единый вызов структурированного ответа поверх instructor для обоих типов клиентов."""
    kwargs = dict(model=model, response_model=response_model, max_tokens=max_tokens, temperature=0)
    if mode == "anthropic":
        kwargs["system"] = system
        kwargs["messages"] = [{"role": "user", "content": user}]
    else:  # openai-совместимый (ollama / yandex)
        kwargs["messages"] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
    return client.chat.completions.create(**kwargs)
