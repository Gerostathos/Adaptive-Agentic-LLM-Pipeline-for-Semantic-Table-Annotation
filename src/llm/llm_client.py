"""
src/llm/llm_client.py
=========================
LLM access layer for the semantic table annotation pipeline.
"""

import os
import time

import requests
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

from Code.src.config import (
    DEFAULT_LLM_PROVIDER,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    LLM_TEMPERATURE,
    LLM_REQUEST_DELAY_SECONDS,
    LLM_API_TIMEOUT_SECONDS,
)


load_dotenv()


PROVIDER_DEFAULT_MODELS = {
    "openai": DEFAULT_OPENAI_MODEL,
    "google": DEFAULT_GOOGLE_MODEL,
    "groq": DEFAULT_GROQ_MODEL,
    "ollama": DEFAULT_OLLAMA_MODEL,
}


def normalize_provider(provider):
    return str(provider).strip().lower()


def default_model_for_provider(provider):
    provider = normalize_provider(provider)
    return PROVIDER_DEFAULT_MODELS.get(provider, DEFAULT_GOOGLE_MODEL)


def required_api_key(provider):
    provider = normalize_provider(provider)

    if provider == "openai":
        return "OPENAI_API_KEY"

    if provider == "google":
        return "GOOGLE_API_KEY"

    if provider == "groq":
        return "GROQ_API_KEY"

    if provider == "ollama":
        return None

    return ""


def validate_provider(provider):
    provider = normalize_provider(provider)
    api_key_name = required_api_key(provider)

    if api_key_name == "":
        return f"ERROR: Unknown provider: {provider}"

    if api_key_name is not None:
        api_key = os.getenv(api_key_name)

        if api_key is None or api_key.strip() == "":
            return f"ERROR: Missing {api_key_name} in .env"

    return None


def ask_llm(prompt, provider=DEFAULT_LLM_PROVIDER, model=None):
    provider = normalize_provider(provider)

    if model is None:
        model = default_model_for_provider(provider)

    validation_error = validate_provider(provider)

    if validation_error is not None:
        return validation_error

    try:
        if LLM_REQUEST_DELAY_SECONDS > 0:
            time.sleep(LLM_REQUEST_DELAY_SECONDS)

        if provider == "openai":
            return ask_openai(prompt, model)

        if provider == "google":
            return ask_google(prompt, model)

        if provider == "groq":
            return ask_groq(prompt, model)

        if provider == "ollama":
            return ask_ollama(prompt, model)

        return f"ERROR: Unknown provider: {provider}"

    except Exception as error:
        return f"ERROR: {error}"


def ask_openai(prompt, model):
    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        timeout=LLM_API_TIMEOUT_SECONDS,
    )

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=LLM_TEMPERATURE,
    )

    return response.output_text.strip()


def ask_google(prompt, model):
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": LLM_TEMPERATURE,
        },
    )

    if response.text:
        return response.text.strip()

    return ""


def ask_groq(prompt, model):
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
        timeout=LLM_API_TIMEOUT_SECONDS,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=LLM_TEMPERATURE,
    )

    content = response.choices[0].message.content

    if content is None:
        return ""

    return content.strip()


def ask_ollama(prompt, model):
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_API_TIMEOUT_SECONDS,
    )

    response.raise_for_status()

    data = response.json()

    return data.get("response", "").strip()


def run_llm_prompt(
    prompt_name,
    values,
    provider=DEFAULT_LLM_PROVIDER,
    model=None,
):
    from Code.src.llm.prompt_manager import format_prompt

    prompt = format_prompt(
        prompt_name=prompt_name,
        values=values,
    )

    answer = ask_llm(
        prompt=prompt,
        provider=provider,
        model=model,
    )

    return prompt, answer
