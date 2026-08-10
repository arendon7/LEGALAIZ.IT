from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

GRAPH_PATH = Path("graphify-out/graph.json")
OUTPUT_PATH = Path("graphify-out/CHATGPT_GRAPH_INDEX.md")


def main() -> None:
    data = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    nodes = data.get("nodes", [])
    edges = data.get("edges", data.get("links", []))

    labels: dict[str, str] = {}
    degree: Counter[str] = Counter()
    kinds: Counter[str] = Counter()

    for node in nodes:
        node_id = str(node.get("id", ""))
        label = str(node.get("label") or node.get("name") or node_id)
        labels[node_id] = label
        kind = str(node.get("type") or node.get("kind") or node.get("category") or "unknown")
        kinds[kind] += 1

    for edge in edges:
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        if source:
            degree[source] += 1
        if target:
            degree[target] += 1

    lines = [
        "# LegalAIZ.it · índice compacto Graphify",
        "",
        "> Archivo generado. Usarlo para orientación rápida; verificar siempre contra el código y el SHA vigente.",
        "",
        f"- Nodos: **{len(nodes)}**",
        f"- Relaciones: **{len(edges)}**",
        "",
        "## Tipos de nodo",
    ]

    if kinds:
        for kind, count in kinds.most_common(20):
            lines.append(f"- `{kind}`: {count}")
    else:
        lines.append("- Sin clasificación disponible en el snapshot.")

    lines.extend(["", "## Nodos más conectados"])
    if degree:
        for node_id, count in degree.most_common(40):
            lines.append(f"- {labels.get(node_id, node_id)} — grado {count}")
    else:
        lines.append("- El snapshot no contiene relaciones utilizables.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
