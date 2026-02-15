# NOVA (Minimal)

> Persistentes Kontextsystem für gezielte Problemlösung.

## Kern-Tools

| Tool | Funktion |
|------|----------|
| `nova_context_resolve` | Kontext selektiv laden |
| `nova_project_continue` | Projekt fortsetzen (3-Schritt-Plan) |
| `nova_project_create` | Projekt anlegen |
| `nova_knowledge_query` | Wissen abfragen |
| `nova_knowledge_update` | Erkenntnis persistieren |
| `nova_system_maintain` | System warten |

## Regeln (3)

1. Persist Results → Erkenntnisse via `nova_knowledge_update`
2. Context First → Erst `nova_context_resolve`, dann handeln
3. Vault = Truth → Chat ist Arbeitsflaeche, nicht Ergebnis
