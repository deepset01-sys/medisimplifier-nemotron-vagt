"""
prompts.py — the simplification prompt the Safe Endpoint serves.

It is the prompt that produced the published v2 evaluation outputs (src/evaluate.py, ChatML format, no native
template): the same instruction, system message and inference template, text for text. evaluate.py keeps its own
copy as the record of how those outputs were made; tests/test_prompts.py fails if the two ever differ.

The model learned to end its answer with the literal "<|im_end|>" marker, which is not a special token for its
tokenizer, so generation must stop on it (STOP) or the model runs on into invented turns.
"""

TASK_INSTRUCTION = """Simplify the following medical discharge summary in plain language for patients with no medical background.
Guidelines:
- Replace medical jargon with everyday words (e.g., "hypertension" → "high blood pressure")
- Keep all important information (diagnoses, medications, follow-up instructions)
- Use short, clear sentences (aim for 15-20 words per sentence)
- Aim for a 6th-grade reading level
- Maintain the same structure as the original
- Do not add or omit information
- Keep the same patient reference style
- Output plain text only (no markdown, no bold, no headers, no bullet points)
- Do not include empty lines or separator characters like ---"""

SYSTEM_MESSAGE = "You are a helpful medical assistant that simplifies complex medical text for patients."

CHATML_INFERENCE = "<|im_start|>system\n{system}<|im_end|>\n<|im_start|>user\n{instruction}\n\n{input}<|im_end|>\n<|im_start|>assistant\n"

STOP = ["<|im_end|>", "<|im_start|>"]


def build_prompt(text: str) -> str:
    """The full prompt for one input, exactly as evaluate.py builds it for the fine-tuned model."""
    return CHATML_INFERENCE.format(system=SYSTEM_MESSAGE, instruction=TASK_INSTRUCTION, input=text)
