"""Compatibility stub retained after Vertex removal."""


class VertexAgentClient:
    """No-op compatibility client. Returns empty results."""

    def search(self, query: str, page_size: int = 20):
        return []

    def get_all_invoices(self, page_size: int = 200):
        return []
