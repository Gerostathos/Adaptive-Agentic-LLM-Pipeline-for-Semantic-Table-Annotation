"""
src/llm/prompt_manager.py
=========================
Load and format prompt templates used by the STA pipeline.
"""

from pathlib import Path

from src.config import DEFAULT_PROMPT_FILE
import yaml

prompt_file = DEFAULT_PROMPT_FILE

def load_prompts(prompt_file=prompt_file):
    """
    Load all prompt templates from a YAML file.

    Parameters:
        prompt_file: Path to the YAML prompt file.

    Returns:
        Dictionary of prompt templates.
    """

    prompt_path = Path(prompt_file)

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    with prompt_path.open("r", encoding="utf-8") as file:
        prompts = yaml.safe_load(file)

    if prompts is None:
        return {}

    return prompts


def get_prompt(prompt_name, prompt_file=prompt_file):
    """
    Get one prompt template by name.

    Parameters:
        prompt_name: Name of the prompt in the YAML file.
        prompt_file: Path to the YAML prompt file.

    Returns:
        Prompt template string.
    """

    prompts = load_prompts(prompt_file)

    if prompt_name not in prompts:
        available = ", ".join(prompts.keys())
        raise KeyError(
            f"Prompt not found: {prompt_name}. "
            f"Available prompts: {available}"
        )

    return prompts[prompt_name]


def format_prompt(prompt_name, values, prompt_file=prompt_file):
    """
    Load a prompt template and fill it with values.

    Parameters:
        prompt_name: Name of the prompt in the YAML file.
        values: Dictionary of placeholder values.
        prompt_file: Path to the YAML prompt file.

    Returns:
        Formatted prompt string.
    """

    template = get_prompt(
        prompt_name=prompt_name,
        prompt_file=prompt_file,
    )

    try:
        return template.format(**values)

    except KeyError as error:
        missing_key = str(error)
        raise KeyError(
            f"Missing value for prompt placeholder: {missing_key}"
        )


def print_available_prompts(prompt_file=prompt_file):
    """
    Print all available prompt names.
    """

    prompts = load_prompts(prompt_file)

    print("\n=== AVAILABLE PROMPTS ===")

    if not prompts:
        print("No prompts found.")
        return

    for prompt_name in prompts:
        print("-", prompt_name)

