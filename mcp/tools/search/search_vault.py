"""
Tool: Search Vault
Semantic search over the indexed vault.
"""

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from .shared import tool_logger, semantic_search


def get_tool_definition(workspace_root: Path) -> Tool:
    return Tool(
        name="nova_search_vault",
        description="Semantische Suche in der Vault. Findet relevante Notes auch ohne exakten Textmatch.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Suchanfrage (natuerliche Sprache)",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Anzahl Ergebnisse (default: 5)",
                    "default": 5,
                },
                "threshold": {
                    "type": "number",
                    "description": "Minimum Similarity Score 0-1 (default: 0.3)",
                    "default": 0.3,
                },
            },
            "required": ["query"],
        },
    )


async def execute(args: dict, workspace_root: Path) -> list[TextContent]:
    """Fuehrt semantische Suche ueber die Vault aus."""
    log = tool_logger("search_vault")
    
    query = args["query"]
    top_k = args.get("top_k", 5)
    threshold = args.get("threshold", 0.3)

    cfg = resolve_paths(workspace_root)
    chroma_path = cfg.chroma_path
    semantic_index_file = cfg.index_root / "semantic_index.json"
    if not semantic_index_file.exists() and not chroma_path.exists():
        return [
            TextContent(
                type="text",
                text="Index nicht gefunden.\\n\\nFuehre zuerst `nova_system_maintain(operation='index')` aus um die Vault zu indexieren.",
            )
        ]

    try:
        items = semantic_search(str(chroma_path), query, top_k, log)
    except ImportError as e:
        return [TextContent(type="text", text=f"[ERROR] Dependencies fehlen: {e}\\n\\nInstalliere mit:\\npip install chromadb sentence-transformers")]
    except RuntimeError as e:
        return [TextContent(type="text", text=f"Semantische Suche derzeit deaktiviert: {e}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Suche fehlgeschlagen ({type(e).__name__}). Fuehre `nova_system_maintain(operation='index')` aus.")]

    output_lines = [f"## Suche: \"{query}\"\\n"]
    if not items:
        output_lines.append("Keine Ergebnisse gefunden.")
        return [TextContent(type="text", text="\\n".join(output_lines))]

    found = 0
    seen_paths = set()
    for item in items:
        doc = item["doc"]
        meta = item["meta"]
        distance = item["distance"]
        similarity = 1 - distance
        if similarity < threshold:
            continue

        path = meta["path"]
        section = meta.get("section", "")
        if path in seen_paths:
            continue
        seen_paths.add(path)

        preview = doc[:200]
        if len(doc) > 200:
            for end in [". ", "! ", "? ", "\\n"]:
                pos = preview.rfind(end)
                if pos > 100:
                    preview = preview[: pos + 1]
                    break
            else:
                preview += "..."

        found += 1
        output_lines.append(f"### {found}. [{path}]({path})")
        if section:
            output_lines.append(f"**Section:** {section}")
        output_lines.append(f"**Score:** {similarity:.2f}")
        output_lines.append(f"```\\n{preview}\\n```\\n")

    if found == 0:
        output_lines.append(f"Keine Ergebnisse ueber Threshold {threshold}.")
    else:
        output_lines.append(f"---\\n*{found} Treffer (Threshold: {threshold})*")

    log("Done")
    return [TextContent(type="text", text="\\n".join(output_lines))]
