from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

GRAPH_PATH = Path("graphify-out/graph.json")
OUTPUT_PATH = Path("graphify-out/CHATGPT_GRAPH_INDEX.md")
FILE_SUFFIXES = (
    ".py",
    ".js",
    ".mjs",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".html",
    ".css",
    ".md",
    ".yml",
    ".yaml",
)


def main() -> None:
    data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    edges = data.get("edges", data.get("links", []))

    labels: dict[str, str] = {}
    degree: Counter[str] = Counter()

    for node in nodes:
        node_id = str(node.get("id", ""))
        label = str(node.get("label") or node.get("name") or node_id)
        labels[node_id] = label

    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source:
            degree[source] += 1
        if target:
            degree[target] += 1

    ranked = degree.most_common()
    files = [
        (node_id, count)
        for node_id, count in ranked
        if labels.get(node_id, "").lower().endswith(FILE_SUFFIXES)
    ][:40]
    symbols = [
        (node_id, count)
        for node_id, count in ranked
        if not labels.get(node_id, "").lower().endswith(FILE_SUFFIXES)
    ][:40]

    lines = [
        "# LegalAIZ.it · índice compacto Graphify",
        "",
        "> Archivo generado. Sirve para orientar la exploración; verificar siempre contra el código y el SHA vigente.",
        "",
        f"- Nodos: **{len(nodes)}**",
        f"- Relaciones: **{len(edges)}**",
        "",
        "## Archivos más conectados",
    ]

    if files:
        for node_id, count in files:
            lines.append(f"- `{labels.get(node_id, node_id)}` — grado {count}")
    else:
        lines.append("- El snapshot no expone archivos clasificables por nombre.")

    lines.extend(["", "## Símbolos más conectados"])
    if symbols:
        for node_id, count in symbols:
            lines.append(f"- `{labels.get(node_id, node_id)}` — grado {count}")
    else:
        lines.append("- El snapshot no contiene símbolos con relaciones utilizables.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
