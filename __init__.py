import json

import nodes
from server import PromptServer

from .policy import categories_from_prompt, filter_stack, inject_category_policy, parse_object
from .presets import register_routes

WEB_DIRECTORY = "./web"


class LoraCategoryControls:
    CATEGORY = "Category LoRA"
    FUNCTION = "show"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("category_settings",)
    OUTPUT_NODE = True
    DESCRIPTION = "One controller for all Category LoRA Loaders in this workflow. No wires needed. Off excludes weights and trigger words; individual row switches are preserved."

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"category_state": ("STRING", {"default": '{"version":1,"categories":{}}', "multiline": True})}}

    def show(self, category_state):
        state = parse_object(category_state, "Category Controls")
        text = json.dumps(state, ensure_ascii=False)
        return {"ui": {"text": [text]}, "result": (text,)}


class CategoryLoraLoader:
    CATEGORY = "Category LoRA"
    FUNCTION = "apply"
    RETURN_TYPES = ("MODEL", "CLIP", "STRING")
    RETURN_NAMES = ("MODEL", "CLIP", "triggers")
    DESCRIPTION = "Pixaroma-style stack with trigger words and multiple category tags per row. Any disabled category blocks the row. Use one Category Controls node anywhere in this workflow."

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"model": ("MODEL",)},
            "optional": {"clip": ("CLIP",)},
            "hidden": {"LoraLoaderState": ("STRING", {"default": "{}"}), "CategoryPolicy": ("STRING", {"default": "{}"}), "prompt": "PROMPT"},
        }

    def apply(self, model, clip=None, LoraLoaderState="{}", CategoryPolicy=None, prompt=None):
        policy = parse_object(CategoryPolicy, "Category policy") if CategoryPolicy is not None else categories_from_prompt(prompt)
        state = filter_stack(LoraLoaderState, policy)
        loader_class = nodes.NODE_CLASS_MAPPINGS.get("PixaromaLoraLoader")
        if loader_class is None:
            raise RuntimeError("Category LoRA requires the installed ComfyUI-Pixaroma node pack.")
        return loader_class().apply(model, clip, json.dumps(state))


NODE_CLASS_MAPPINGS = {"CategoryLoraLoader": CategoryLoraLoader, "LoraCategoryControls": LoraCategoryControls}
NODE_DISPLAY_NAME_MAPPINGS = {"CategoryLoraLoader": "Category LoRA Loader", "LoraCategoryControls": "LoRA Category Controls"}

# The snapshot travels with the queued prompt, including API submissions. No
# process-global category state or frontend-only cache invalidation is needed.
PromptServer.instance.add_on_prompt_handler(inject_category_policy)
register_routes(PromptServer.instance)
