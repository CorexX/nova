"""
Tool: Search Vault
Semantic search over the indexed vault.
"""

from pathlib import Path

from mcp.types import TextContent, Tool

from ..paths import resolve_paths
from .shared import get_chromadb, get_model


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
    import sys
    import time
    from mcp import server as mcp_server

    try:
        chromadb = get_chromadb()
        start = time.time()
        model = get_model()
        elapsed = time.time() - start
        if elapsed > 1.0:
            print(f"[search_vault] Model loaded ({elapsed:.1f}s)", file=sys.stderr, flush=True)
    except ImportError as e:
        return [
            TextContent(
                type="text",
                text=f"[ERROR] Dependencies fehlen: {e}\\n\\nInstalliere mit:\\npip install chromadb sentence-transformers",
            )
        ]

    query = args["query"]
    top_k = args.get("top_k", 5)
    threshold = args.get("threshold", 0.3)

    wait_for_model = getattr(mcp_server, "wait_for_model", None)
    if callable(wait_for_model):
        ready = await wait_for_model()
        if not ready:
            return [TextContent(type="text", text="Modell l\u00e4dt noch, bitte gleich erneut versuchen.")]

    chroma_path = resolve_paths(workspace_root).chroma_path
    if not chroma_path.exists():
        return [
            TextContent(
                type="text",
                text="Index nicht gefunden.\\n\\nFuehre zuerst `nova_index_vault()` aus um die Vault zu indexieren.",
            )
        ]

    client = chromadb.PersistentClient(path=str(chroma_path))
    try:
        collection = client.get_collection("vault")
    except Exception:
        return [
            TextContent(
                type="text",
                text="Collection 'vault' nicht gefunden.\\n\\nFuehre `nova_index_vault()` aus.",
            )
        ]

    query_embedding = model.encode(query).tolist()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    output_lines = [f"## Suche: \"{query}\"\\n"]
    if not results["ids"][0]:
        output_lines.append("Keine Ergebnisse gefunden.")
        return [TextContent(type="text", text="\\n".join(output_lines))]

    found = 0
    seen_paths = set()
    for doc, meta, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
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

    return [TextContent(type="text", text="\\n".join(output_lines))]
