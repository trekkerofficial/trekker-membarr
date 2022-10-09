# Converts a comma separated string to a list
def str_to_list(string: str) -> list[str]:
    # input is empty, or None
    if not string:
        return []
    return list(map(lambda elem: elem.strip(), string.split(",")))
