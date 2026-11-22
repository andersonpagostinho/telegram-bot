"""
OpenAI API Client with Structured Outputs support
"""

import os
import json
from typing import Dict, Any

class OpenAIClient:
    """Wrapper for OpenAI API with Structured Outputs"""

    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.timeout = int(os.getenv("OPENAI_VALIDATOR_TIMEOUT", "30"))

    def call_validation_api(self, prompt: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Call OpenAI API with Structured Outputs"""

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        try:
            # Import OpenAI library (must be installed separately)
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            response = client.beta.messages.create(
                model=self.model,
                max_tokens=1024,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                betas=["interop-2024-12-06"]
            )

            # Parse structured output
            result = json.loads(response.content[0].text)

            return {
                "verdict": result.get("verdict", "NEEDS_HUMAN_REVIEW"),
                "confidence": result.get("confidence", 0),
                "findings": result.get("findings", []),
                "summary": result.get("summary", ""),
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }
            }

        except ImportError:
            raise ImportError("openai library required: pip install openai>=1.0.0")
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}")

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for GPT-4 Turbo"""
        # GPT-4 Turbo: $0.01 per 1K input tokens, $0.03 per 1K output tokens
        return (input_tokens / 1000 * 0.01) + (output_tokens / 1000 * 0.03)
