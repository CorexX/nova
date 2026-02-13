# Ingestion Pipeline mit `nova-server` (Telegram -> Erkenntnisse -> Vault)

## Ziel

Telegram-Nachrichten (Links, kurzer Text, spaeter Medien) automatisch aufnehmen, verarbeiten und strukturiert in `nova-knowledge` ablegen.

## Architektur-Entscheidung

- Runtime und Orchestrierung laufen in `nova-server` (Homeserver Deployment).
- `nova-core` bleibt der wiederverwendbare Wissens-/Tool-Kern.
- n8n ist optionaler Orchestrator und passt gut fuer Trigger, Retry und Monitoring.

## MVP Scope (Phase 1)

1. Telegram Input (nur erlaubte Chat IDs)
2. URL/Text-Erkennung
3. Content-Extraktion (URL -> Haupttext; Text -> direkt)
4. LLM-Extraktion in strikt validiertes JSON
5. Persistenz:
   - Append in `INBOX.md`
   - Strukturierte Knowledge-Note in `nova-knowledge/.../knowledge/`
6. Telegram-Reply mit kurzer Zusammenfassung

## Datenfluss

1. Telegram -> `nova-server` Webhook/Polling
2. Normalisierung (URL bereinigen, Duplikate checken)
3. Extraktion (Artikeltext / Originaltext)
4. LLM Prompt -> JSON Schema
5. Markdown-Writer + optional WORKLOG-Eintrag
6. Ergebnis an Telegram zurueck

## JSON Schema (Arbeitsvertrag)

```json
{
  "source_type": "url|text",
  "source_url": "string|null",
  "title": "string",
  "summary_short": "string",
  "insights": ["string"],
  "actions": ["string"],
  "tags": ["string"],
  "confidence": 0.0,
  "captured_at": "ISO-8601"
}
```

## Dateiablage (MVP)

- Rohdaten: `nova-knowledge/INBOX.md` (append-only)
- Strukturierte Note:
  - default: `nova-knowledge/knowledge/ingestion/YYYY-MM-DD-<slug>.md`
  - optional spaeter: automatische Zuordnung zu Kunde/Kompetenz

## Beispiel-Markdown

```md
# <Titel>

- Quelle: <URL oder Telegram-Text>
- Erfasst: <ISO timestamp>
- Confidence: <0.00-1.00>
- Tags: #tag1 #tag2

## Kurzfassung
<3-5 Saetze>

## Erkenntnisse
- ...
- ...

## Moegliche Aktionen
- [ ] ...
```

## Guardrails

- Nur Whitelist-Chat IDs
- Dedup (z. B. URL Hash + 7 Tage Fenster)
- Max Input-Groesse pro Nachricht/Quelle
- `confidence < 0.6` markieren als "unsicher"
- Nie bestehende Knowledge-Notes ueberschreiben

## n8n-Integration (empfohlen)

- Node 1: Telegram Trigger
- Node 2: Switch (URL vs Text)
- Node 3: HTTP/Python Worker (Ingestion API)
- Node 4: Persist/Notify
- Node 5: Error Handler + Retry + Dead Letter

## Umsetzung in drei Iterationen

1. Iteration A (Capture):
   - Telegram -> INBOX.md + ACK
2. Iteration B (Extraction):
   - URL/Text -> JSON Extraktion -> Knowledge-Note
3. Iteration C (Operational):
   - Retry, Monitoring, Metrics, dedizierte Error-Queue

## Offene Entscheidungen

1. LLM Provider fuer Ingestion (Azure/OpenAI/Anthropic)
2. Storage fuer dedup + processing state (SQLite vs LiteFS vs Redis)
3. Zielpfad-Mapping (global `knowledge/ingestion/` vs kontextbezogen)
