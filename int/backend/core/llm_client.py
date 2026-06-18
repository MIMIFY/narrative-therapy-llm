import asyncio
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from ..config import settings


class LLMClient:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )

    async def chat(
        self,
        system_prompt: str,
        user_message: str,
        model: str,
        history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.5,
        top_p: float = 0.85,
        max_tokens: int = 512,
        stream: bool = False,
        max_retries: int = 3,
    ) -> Any:
        """
        Send a chat completion request.

        When ``stream=False`` returns the assistant message string.
        When ``stream=True`` returns the raw async streaming response object;
        the caller is responsible for iterating over it.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        backoff = 2.0
        for attempt in range(max_retries):
            try:
                if stream:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        stream=True,
                    )
                    return response  # caller handles streaming
                else:
                    response = await self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        top_p=top_p,
                        max_tokens=max_tokens,
                        stream=False,
                    )
                    return response.choices[0].message.content
            except Exception:
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 1.5

        # unreachable, but satisfies type checker
        return ""


llm_client = LLMClient()
