
# utils/llm_utils.py
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

import json
import time
import requests
from pathlib import Path
from typing import Optional

def load_prompt(prompts_dir: Path,template_name: str,role: str,**kwargs: Any) -> str:
    """
    Loads and renders a Jinja2 prompt template for a given role.

    Args:
        prompts_dir  : Path to directory containing prompt templates.
        template_name: Name of the template file (e.g. 'prompt_extraction.j2').
        role: Either 'system' or 'user'.
        **kwargs : Variables to pass to the template for rendering.

    Returns:
        Rendered prompt string for the given role.

    Example:
        system_prompt = load_prompt(PROMPTS_DIR, "prompt_extraction.j2", role="system")
        user_prompt   = load_prompt(PROMPTS_DIR, "prompt_extraction.j2", role="user",
                                    allowed_subcategories=[...], product_description="...")
    """
    env      = Environment(loader=FileSystemLoader(str(prompts_dir)))

    template = env.get_template(template_name)

    return template.render(role=role, **kwargs)

# utils/config.py — adiciona essa função no final

def load_prompt_template_raw(prompts_dir: Path, template_name: str) -> str:
    """
    Reads the raw Jinja2 template file as a string.
    Used for MLflow logging — logs the template structure,
    not the rendered prompt with specific values.
    """
    template_path = prompts_dir / template_name
    with open(template_path, "r") as f:
        return f.read()
    
def call_llm(
    messages : list,
    api_key  : str,
    api_url  : str,
    model    : str,
    temperature  : float = 0.1,
    max_tokens   : int   = 200,
    timeout      : int   = 30
) -> dict:
    """
    Generic LLM API call. Knows nothing about prompts or business logic.
    Receives a list of messages and returns the response with observability data.

    Args:
        messages   : List of {"role": ..., "content": ...} dicts
        api_key    : API key for authentication
        api_url    : Full API endpoint URL
        model      : Model name to use
        temperature: Sampling temperature (default 0.1 for deterministic output)
        max_tokens : Maximum tokens in response
        timeout    : Request timeout in seconds

    Returns:
        dict with:
            response_text  : raw text response from the LLM
            input_tokens   : tokens consumed in input
            output_tokens  : tokens consumed in output
            total_tokens   : total tokens consumed
            latency_seconds: API response time in seconds

    Raises:
        ValueError: if the API returns a non-200 status code
    """
    payload = {
        "model"      : model,
        "messages"   : messages,
        "temperature": temperature,
        "max_tokens" : max_tokens
    }

    start_time = time.time()

    response = requests.post(
        api_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        json=payload,
        timeout=timeout
    )

    latency = round(time.time() - start_time, 3)

    if response.status_code != 200:
        raise ValueError(f"API error {response.status_code}: {response.text}")

    response_json = response.json()
    response_text = response_json["choices"][0]["message"]["content"]
    usage         = response_json.get("usage", {})

    return {
        "response_text" : response_text,
        "input_tokens"  : usage.get("prompt_tokens", 0),
        "output_tokens" : usage.get("completion_tokens", 0),
        "total_tokens"  : usage.get("total_tokens", 0),
        "latency_seconds": latency
    }