"""
The endpoint's prompt (src/prompts.py) must stay identical to the prompt behind the published v2 evaluation outputs
(src/evaluate.py, ChatML format, no native template). Offline; evaluate.py is parsed, not imported (it needs torch).
"""
import ast
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
import prompts  # noqa: E402


def _evaluate_constants():
    tree = ast.parse((REPO / "src" / "evaluate.py").read_text(encoding="utf-8"))
    out = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            out[node.targets[0].id] = node.value.value
    return out


def test_prompt_text_matches_evaluate_py():
    ev = _evaluate_constants()
    assert prompts.TASK_INSTRUCTION == ev["TASK_INSTRUCTION"]
    assert prompts.SYSTEM_MESSAGE == ev["SYSTEM_MESSAGE"]
    assert prompts.CHATML_INFERENCE == ev["CHATML_INFERENCE"]


def test_build_prompt_is_evaluate_py_chatml_prompt():
    ev = _evaluate_constants()
    text = "Patient has {braces} and type 2 diabetes."
    assert prompts.build_prompt(text) == ev["CHATML_INFERENCE"].format(
        system=ev["SYSTEM_MESSAGE"], instruction=ev["TASK_INSTRUCTION"], input=text)
    assert prompts.build_prompt(text).endswith("<|im_start|>assistant\n")


def test_stop_markers():
    assert prompts.STOP == ["<|im_end|>", "<|im_start|>"]
