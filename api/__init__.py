"""QuantOS Desktop's local application layer (WP-011, ADR-036).

Thin, read-mostly REST layer over the system's real artifacts, bound
to 127.0.0.1 only (Constitution Part III/Security). collectors.py
holds the shared read models (also consumed by the static console
generator); server.py serves the desktop UI (app.html) plus the JSON
API, including the one permitted write control -- the kill switch
(ADR-028) -- and read-only broker account verification. Broker
credentials live in process memory only, never on disk.
"""
