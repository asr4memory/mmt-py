from datetime import datetime


def upload_job_directory_name(title: str, date: datetime) -> str:
    assert isinstance(title, str)
    assert isinstance(date, datetime)
    safe_title = filename_safe(title)
    date_suffix = date.strftime(".%Y-%m-%dT%H%M%SZ")
    return safe_title + date_suffix


def filename_safe(text: str) -> str:
    assert isinstance(text, str)
    keepcharacters = (" ", ".", "_")
    result = "".join(c for c in text if c.isalnum() or c in keepcharacters).rstrip()
    return result
