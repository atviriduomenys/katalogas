def strip_empty_lines(text: str) -> str:
    result = []
    for line in text.splitlines():
        if line.strip():
            result.append(line)
    return '\n'.join(result)
