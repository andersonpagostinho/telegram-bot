#gpt client
import os
from openai import AsyncOpenAI

# Reusable OpenAI client for GPT interactions
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
