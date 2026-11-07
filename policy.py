"""Category decisions are scoped to one queued prompt, never process-wide."""
import copy
import json

CONTROLLER = "LoraCategoryControls"


def parse_object(value, label):
    result = json.loads(value) if isinstance(value, str) else value
    if not isinstance(result, dict):
        raise ValueError(f"{label} must be a JSON object.")
    return result


def categories_from_prompt(prompt):
    controls = [node for node in (prompt or {}).values() if node.get("class_type") == CONTROLLER]
    if len(controls) > 1:
        raise ValueError("Use one Category Controls node per workflow; multiple controllers are ambiguous.")
    if not controls:
        return {}
    state = parse_object(controls[0].get("inputs", {}).get("category_state", "{}"), "Category Controls")
    categories = state.get("categories", {})
    if not isinstance(categories, dict):
        raise ValueError("Category Controls categories must map category names to on/off values.")
    result = {}
    for name, enabled in categories.items():
        if not isinstance(enabled, bool):
            raise ValueError(f"Category '{name}' must have a boolean on/off value.")
        key = str(name).strip().lower()
        if key in result and result[key] != enabled:
            raise ValueError(f"Conflicting switches for category '{name}'.")
        if key:
            result[key] = enabled
    return result


def filter_stack(raw_state, policy):
    state = copy.deepcopy(parse_object(raw_state, "LoRA stack"))
    for row in state.get("loras", []):
        tags = row.get("categories", [])
        if not isinstance(tags, list):
            raise ValueError("Each LoRA's categories must be a list of names.")
        if any(policy.get(str(tag).strip().lower(), True) is False for tag in tags):
            row["on"] = False
    return state


def policy_signature(prompt):
    return json.dumps(categories_from_prompt(prompt), sort_keys=True)


def inject_category_policy(data):
    prompt = data.get("prompt", {})
    if any(node.get("class_type") == "CategoryLoraLoader" for node in prompt.values()):
        payload = policy_signature(prompt)
        for node in prompt.values():
            if node.get("class_type") == "CategoryLoraLoader":
                node.setdefault("inputs", {})["CategoryPolicy"] = payload
    return data
