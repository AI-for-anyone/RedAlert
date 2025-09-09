from pathlib import Path

# 加载提示词
def load_classify_prompt(path: str) -> str:
    _prompt_path = Path(__file__).with_name(path)
    try:
        return _prompt_path.read_text(encoding="utf-8")
    except Exception:
        return ""

classify_prompt = load_classify_prompt("classify_prompt.md")
unit_control_prompt = load_classify_prompt("unit_control_prompt.md")
ai_assistant_prompt: str = load_classify_prompt("ai_assistant_prompt.md")

if __name__ == "__main__":
    print(classify_prompt)