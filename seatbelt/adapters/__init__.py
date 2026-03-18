"""
seatbelt/adapters/__init__.py

Ready-made adapters for common model APIs.

Instead of writing the model_fn wrapper yourself, use one of these:

    from seatbelt.adapters import OpenAIAdapter, OllamaAdapter

    model = OpenAIAdapter(model="gpt-4o")
    report = audit(model, context="customer support")

Each adapter is a callable class — you can pass it directly as model_fn.
They handle auth, retries, and response parsing for you.
"""

from __future__ import annotations
from typing import Optional


class OpenAIAdapter:
    """
    Adapter for the OpenAI Chat Completions API.

    Install extra: pip install seatbelt[openai]

    Usage:
        from seatbelt.adapters import OpenAIAdapter
        model = OpenAIAdapter(model="gpt-4o", temperature=0.0)
        report = audit(model, context="support bot")
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        temperature: float = 0.0,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI adapter requires the openai package. "
                "Install it with: pip install seatbelt[openai]"
            )
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.system_prompt = system_prompt

    def __call__(self, prompt: str) -> str:
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
        )
        return response.choices[0].message.content

    def __repr__(self) -> str:
        return f"OpenAIAdapter(model={self.model!r})"


class AnthropicAdapter:
    """
    Adapter for the Anthropic Claude API.

    Install extra: pip install anthropic

    Usage:
        from seatbelt.adapters import AnthropicAdapter
        model = AnthropicAdapter(model="claude-sonnet-4-20250514")
        report = audit(model, context="research assistant")
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 1024,
        system_prompt: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "Anthropic adapter requires the anthropic package. "
                "Install it with: pip install anthropic"
            )
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt

    def __call__(self, prompt: str) -> str:
        kwargs = dict(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        if self.system_prompt:
            kwargs["system"] = self.system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text

    def __repr__(self) -> str:
        return f"AnthropicAdapter(model={self.model!r})"


class HuggingFaceAdapter:
    """
    Adapter for HuggingFace Transformers (local models).

    Install extra: pip install seatbelt[huggingface]

    Usage:
        from seatbelt.adapters import HuggingFaceAdapter
        model = HuggingFaceAdapter("mistralai/Mistral-7B-Instruct-v0.2")
        report = audit(model, context="coding assistant")
    """

    def __init__(
        self,
        model_name: str,
        max_new_tokens: int = 512,
        device: str = "auto",
        load_in_4bit: bool = False,
    ):
        try:
            from transformers import pipeline, BitsAndBytesConfig
            import torch
        except ImportError:
            raise ImportError(
                "HuggingFace adapter requires transformers and torch. "
                "Install with: pip install seatbelt[huggingface]"
            )

        quant_config = None
        if load_in_4bit:
            quant_config = BitsAndBytesConfig(load_in_4bit=True)

        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            device_map=device,
            model_kwargs={"quantization_config": quant_config} if quant_config else {},
        )
        self.max_new_tokens = max_new_tokens
        self.model_name = model_name

    def __call__(self, prompt: str) -> str:
        result = self.pipe(
            prompt,
            max_new_tokens=self.max_new_tokens,
            do_sample=False,
            return_full_text=False,
        )
        return result[0]["generated_text"].strip()

    def __repr__(self) -> str:
        return f"HuggingFaceAdapter(model={self.model_name!r})"


class OllamaAdapter:
    """
    Adapter for Ollama (local model server).
    Requires Ollama running at http://localhost:11434.

    Install Ollama: https://ollama.com
    Pull a model:   ollama pull llama3

    Usage:
        from seatbelt.adapters import OllamaAdapter
        model = OllamaAdapter("llama3")
        report = audit(model, context="general assistant")
    """

    def __init__(
        self,
        model: str = "llama3",
        host: str = "http://localhost:11434",
        system_prompt: Optional[str] = None,
    ):
        self.model = model
        self.host = host
        self.system_prompt = system_prompt

    def __call__(self, prompt: str) -> str:
        try:
            import ollama
            messages = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": prompt})
            response = ollama.chat(model=self.model, messages=messages)
            return response["message"]["content"]
        except ImportError:
            # Fall back to raw HTTP if ollama package not installed
            import urllib.request
            import json
            payload = json.dumps({
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            }).encode()
            req = urllib.request.Request(
                f"{self.host}/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
                return data["message"]["content"]

    def __repr__(self) -> str:
        return f"OllamaAdapter(model={self.model!r}, host={self.host!r})"


__all__ = [
    "OpenAIAdapter",
    "AnthropicAdapter",
    "HuggingFaceAdapter",
    "OllamaAdapter",
]
