from pathlib import Path
from typing import Dict
import logging

logger = logging.getLogger(__name__)

_PROMPT_CACHE: Dict[str, str] = {}


def load_prompt(prompt_name: str, reload: bool = False) -> str:
    if not reload and prompt_name in _PROMPT_CACHE:
        return _PROMPT_CACHE[prompt_name]

    prompt_dir = Path(__file__).parent.parent / 'prompts'
    prompt_file = prompt_dir / f"{prompt_name}.txt"

    if not prompt_file.exists():
        logger.error(f"Prompt file not found: {prompt_file}")
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            prompt = f.read()

        _PROMPT_CACHE[prompt_name] = prompt
        logger.info(f"Loaded prompt: {prompt_name} ({len(prompt)} chars)")
        return prompt

    except Exception as e:
        logger.error(f"Failed to load prompt {prompt_name}: {e}")
        raise


def clear_prompt_cache():
    global _PROMPT_CACHE
    _PROMPT_CACHE = {}
    logger.info("Prompt cache cleared")
