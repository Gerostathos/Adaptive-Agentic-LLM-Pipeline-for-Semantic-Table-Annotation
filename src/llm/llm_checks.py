"""
src/llm/llm_checks.py

Small manual LLM test utility.
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from openai import OpenAI

from src.config import (
    DEFAULT_OPENAI_MODEL,
    DEFAULT_GOOGLE_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_OLLAMA_MODEL,
    OLLAMA_BASE_URL,
    LLM_API_TIMEOUT_SECONDS,
)

from src.llm.llm_client import ask_llm


load_dotenv()


def safe_error(error):
    text = str(error)

    for key_name in ["OPENAI_API_KEY", "GOOGLE_API_KEY", "GROQ_API_KEY"]:
        key = os.getenv(key_name)

        if key and len(key) > 10:
            text = text.replace(key, key[:6] + "..." + key[-4:])

    return f"ERROR: {text}"


def list_openai_models():
    try:
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=LLM_API_TIMEOUT_SECONDS,
        )
        return sorted(model.id for model in client.models.list().data)
    except Exception as error:
        return [safe_error(error)]


def list_google_models():
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        return sorted(model.name for model in client.models.list())
    except Exception as error:
        return [safe_error(error)]


def list_groq_models():
    try:
        client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1",
            timeout=LLM_API_TIMEOUT_SECONDS,
        )
        return sorted(model.id for model in client.models.list().data)
    except Exception as error:
        return [safe_error(error)]


def list_ollama_models():
    try:
        response = requests.get(
            f"{OLLAMA_BASE_URL}/api/tags",
            timeout=LLM_API_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        data = response.json()
        return sorted(model["name"] for model in data.get("models", []))
    except Exception:
        return ["ERROR: Ollama is not running. Start it with: ollama serve"]


def save_available_models_to_log():
    Path("logs").mkdir(exist_ok=True)

    provider_models = {
        "OpenAI": list_openai_models(),
        "Google Gemini": list_google_models(),
        "Groq": list_groq_models(),
        "Ollama": list_ollama_models(),
    }

    lines = [
        "AVAILABLE LLM MODELS",
        "====================",
        "",
    ]

    for provider, models in provider_models.items():
        lines.append(f"{provider}:")

        for model in models:
            lines.append(f" - {model}")

        lines.append("")

    output_path = Path("logs/available_models.txt")
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved: {output_path}")


def compare_llms(prompt):
    tests = {
        f"openai:{DEFAULT_OPENAI_MODEL}": ("openai", DEFAULT_OPENAI_MODEL),
        f"google:{DEFAULT_GOOGLE_MODEL}": ("google", DEFAULT_GOOGLE_MODEL),
        f"groq:{DEFAULT_GROQ_MODEL}": ("groq", DEFAULT_GROQ_MODEL),
        f"ollama:{DEFAULT_OLLAMA_MODEL}": ("ollama", DEFAULT_OLLAMA_MODEL),
    }

    results = {}

    for label, (provider, model) in tests.items():
        print(f"Testing {label}")

        results[label] = ask_llm(
            prompt=prompt,
            provider=provider,
            model=model,
        )

    return results


def save_llm_test_results(results):
    Path("logs").mkdir(exist_ok=True)

    lines = [
        "LLM COMPARISON TEST RESULTS",
        "===========================",
        "",
    ]

    for model_name, answer in results.items():
        lines.append(f"Model: {model_name}")
        lines.append("Answer:")
        lines.append(str(answer).strip())
        lines.append("")

    output_path = Path("logs/llm_test_results.txt")
    output_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Saved: {output_path}")


if __name__ == "__main__":
    save_available_models_to_log()

    test_prompt = """
        You are helping with semantic table annotation.

        Given these values from one table column:
        Inception
        Titanic
        Avatar
        Interstellar

        Return a short semantic topic for this column.
        Return only the topic.
        """.strip()

    results = compare_llms(test_prompt)
    save_llm_test_results(results)

    print("\n=== LLM COMPARISON TEST ===")

    for model_name, answer in results.items():
        print("\nModel:", model_name)
        print("Answer:", answer)