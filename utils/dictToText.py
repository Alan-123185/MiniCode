def dict_to_text(d: dict, indent: int = 0) -> str:
    pad = " " * indent
    lines = []

    for key, value in d.items():
        if value in (None, "", [], {}):
            continue

        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(dict_to_text(value, indent + 2))

        elif isinstance(value, list):
            lines.append(f"{pad}{key}:")
            for item in value:
                if isinstance(item, dict):
                    sub = dict_to_text(item, indent + 2).splitlines()
                    if sub:
                        # 第一行加 "- "，其余行对齐到 "- " 之后
                        lines.append(f"{pad}  - {sub[0].strip()}")
                        lines.extend(" " * (indent + 4) + l.strip() for l in sub[1:])
                else:
                    lines.append(f"{pad}  - {item}")

        else:
            if isinstance(value, str) and "\n" in value:
                value = " ".join(value.split())
            lines.append(f"{pad}{key}: {value}")

    return "\n".join(l for l in lines if l.strip())