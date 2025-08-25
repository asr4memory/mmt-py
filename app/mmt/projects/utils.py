def filename_safe(text: str) -> str:
    assert isinstance(text, str)
    keepcharacters = (" ", ".", "_")
    result = "".join(c for c in text if c.isalnum() or c in keepcharacters).rstrip()
    result = result.replace(" ", "_")
    return result
