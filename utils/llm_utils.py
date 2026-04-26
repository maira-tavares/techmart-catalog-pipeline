
# utils/llm_utils.py
from pathlib import Path
from typing import Any
from jinja2 import Environment, FileSystemLoader

import json
import time
import requests
from pathlib import Path
from typing import Optional
import json
from pydantic import ValidationError

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
    messages    : list,
    api_key     : str,
    api_url     : str,
    model       : str,
    temperature : float = 0.1,
    max_tokens  : int   = 200,
    timeout     : int   = 60,
    max_retries : int   = 5,
    retry_delay : float = 20.0,
    output_model        = None  # Optional Pydantic model for JSON validation
) -> dict:
    """
    Generic LLM API call with exponential backoff retry logic.
    Compatible with any OpenAI-format API (Groq, OpenAI, etc.)

    If output_model is provided:
        - Parses response as JSON
        - Validates against the Pydantic model
        - Retries if validation fails
    If output_model is None:
        - Returns raw response text
        - No JSON parsing or validation

    Args:
        messages    : List of {"role": ..., "content": ...} dicts.
        api_key     : API key for authentication.
        api_url     : Full API endpoint URL.
        model       : Model name.
        temperature : Sampling temperature.
        max_tokens  : Max tokens in response.
        timeout     : Request timeout in seconds.
        max_retries : Maximum retry attempts.
        retry_delay : Base delay in seconds — doubles on each retry.
        output_model: Optional Pydantic model class to validate JSON response.
                      e.g. ProductExtraction, JudgeResult, or None.

    Returns:
        dict with response_text, input_tokens, output_tokens,
        total_tokens, latency_seconds, attempt_number.
        If output_model is provided, also includes validated_output.

    Raises:
        ValueError: if all retry attempts fail.
    """

    payload = {
        "model"      : model,
        "messages"   : messages,
        "temperature": temperature,
        "max_tokens" : max_tokens
    }

    last_error  = None
    total_start = time.time()

    for attempt in range(1, max_retries + 1):

        try:
            attempt_start = time.time()

            response = requests.post(
                api_url,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                },
                json=payload,
                timeout=timeout
            )

            latency = round(time.time() - attempt_start, 3)

            # ── Status 200: HTTP success ──────────────────────────────────────
            if response.status_code == 200:
                response_json = response.json()
                response_text = response_json["choices"][0]["message"]["content"]
                usage         = response_json.get("usage", {})

                base_result = {
                    "response_text"  : response_text,
                    "input_tokens"   : usage.get("prompt_tokens", 0),
                    "output_tokens"  : usage.get("completion_tokens", 0),
                    "total_tokens"   : usage.get("total_tokens", 0),
                    "latency_seconds": latency,
                    "attempt_number" : attempt
                }

                # ── Optional output validation ────────────────────────────────
                # Only runs if caller passed a Pydantic model
                # If not passed → returns raw response immediately
                if output_model is not None:
                    try:
                        # Step 1 — Clean markdown formatting
                        clean = (
                            response_text
                            .strip()
                            .replace("```json", "")
                            .replace("```", "")
                            .strip()
                        )

                        # Step 2 — Parse JSON string into Python dict
                        parsed = json.loads(clean)

                        # Step 3 — Validate dict against Pydantic model
                        validated = output_model(**parsed)

                        # ✅ Validation passed — add to result and return
                        base_result["validated_output"] = validated
                        return base_result

                    except (ValidationError, json.JSONDecodeError, KeyError) as ve:
                        # ❌ Validation failed — retry
                        # The HTTP call worked but the content is wrong
                        wait_time = retry_delay * (2 ** (attempt - 1))
                        print(f"⚠️ Output validation failed (attempt {attempt}/{max_retries}): {ve}. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        last_error = f"Output validation error: {ve}"
                        continue

                # ── No output_model — return raw response ─────────────────────
                return base_result

            # ── Status 429: rate limit ────────────────────────────────────────
            elif response.status_code == 429:
                wait_time = retry_delay * (2 ** (attempt - 1))
                print(f"⚠️ Rate limit (attempt {attempt}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                last_error = f"Rate limit: {response.text}"

            # ── Other API errors ──────────────────────────────────────────────
            else:
                wait_time = retry_delay * (2 ** (attempt - 1))
                print(f"⚠️ API error {response.status_code} (attempt {attempt}/{max_retries}). Waiting {wait_time}s...")
                time.sleep(wait_time)
                last_error = f"API error {response.status_code}: {response.text}"

        # ── Network timeout ───────────────────────────────────────────────────
        except requests.exceptions.Timeout:
            wait_time = retry_delay * (2 ** (attempt - 1))
            print(f"⚠️ Timeout (attempt {attempt}/{max_retries}). Waiting {wait_time}s...")
            time.sleep(wait_time)
            last_error = "Request timeout"

        # ── Connection error ──────────────────────────────────────────────────
        except requests.exceptions.ConnectionError:
            wait_time = retry_delay * (2 ** (attempt - 1))
            print(f"⚠️ Connection error (attempt {attempt}/{max_retries}). Waiting {wait_time}s...")
            time.sleep(wait_time)
            last_error = "Connection error"

    # ── All retries exhausted ─────────────────────────────────────────────────
    total_time = round(time.time() - total_start, 3)
    raise ValueError(
        f"All {max_retries} attempts failed after {total_time}s. "
        f"Last error: {last_error}"
    )