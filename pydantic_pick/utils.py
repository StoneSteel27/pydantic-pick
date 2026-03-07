from typing import Dict, Any


def build_include_dict(paths: list[str]) -> Dict[str, Any]:
    """
    Converts a flat list of dot-notation strings into a nested dictionary structure
    suitable for recursive Pydantic model extraction.

    Example:
        Input: ["id", "profile.city", "profile.settings.theme"]
        Output: {
            "id": True, 
            "profile": {
                "city": True,
                "settings": {"theme": True}
            }
        }

    Args:
        paths (list[str]): A list of string paths to retain from the model.

    Returns:
        Dict[str, Any]: A nested dictionary mapping where leaf nodes are True.
    """
    result: Dict[str, Any] = {}

    for path in paths:
        parts = path.split('.')
        current = result

        for i, part in enumerate(parts):
            is_last_part = (i == len(parts) - 1)

            if is_last_part:
                # If we've reached the end of the dot-notation path,
                # mark it True unless it's already a dictionary from a deeper path.
                if part not in current or current[part] is True:
                    current[part] = True
            else:
                # For intermediate steps, we must ensure a dictionary exists
                # so we can continue nesting deeper.
                if part not in current or current[part] is True:
                    current[part] = {}

                # Move the reference deeper into the tree
                current = current[part]

    return result
