"""Vertex AI Agent Builder integration for fetching real data."""

import requests
import json
from datetime import datetime
from google.auth import default
from google.auth.transport.requests import Request


class VertexAgentClient:
    """Client for querying Vertex AI Agent Builder Discovery Engine."""

    PROJECT_NUM = "972191003940"
    PROJECT_ID = "project-899e2ec5-c891-4b57-9bb"
    ENGINE_ID = "v2dataset_1772169095805"
    DATA_STORE_ID = "v2-twoanalyst-arcollection_1772169012145"

    def __init__(self):
        self.creds, _ = default()
        self._refresh_token()

    def _refresh_token(self):
        self.creds.refresh(Request())

    def _headers(self):
        # Refresh if token is expired
        if not self.creds.valid:
            self._refresh_token()
        return {
            "Authorization": f"Bearer {self.creds.token}",
            "x-goog-user-project": self.PROJECT_ID,
            "Content-Type": "application/json",
        }

    def search(self, query: str, page_size: int = 50, filter_str: str = None) -> list:
        """Search the data store and return structured results."""
        url = (
            f"https://discoveryengine.googleapis.com/v1/projects/{self.PROJECT_NUM}"
            f"/locations/global/collections/default_collection"
            f"/engines/{self.ENGINE_ID}/servingConfigs/default_search:search"
        )
        payload = {
            "query": query,
            "pageSize": page_size,
        }
        if filter_str:
            payload["filter"] = filter_str

        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            doc = r.get("document", {}).get("structData", {})
            if doc:
                results.append(doc)
        return results

    def get_all_invoices(self, page_size: int = 100) -> list:
        """Fetch all invoices from the data store."""
        return self.search("all invoices", page_size=page_size)

    def get_overdue_invoices(self, page_size: int = 50) -> list:
        """Fetch overdue/open invoices."""
        return self.search("overdue open invoices", page_size=page_size)

    def get_invoices_by_analyst(self, analyst_id: str, page_size: int = 50) -> list:
        """Fetch invoices for a specific analyst."""
        return self.search(f"invoices for analyst {analyst_id}", page_size=page_size)

    def get_invoices_by_customer(self, customer_name: str, page_size: int = 20) -> list:
        """Fetch invoices for a specific customer."""
        return self.search(f"invoices for customer {customer_name}", page_size=page_size)

    def answer_question(self, question: str) -> str:
        """Use the answer endpoint to get an AI-generated answer."""
        url = (
            f"https://discoveryengine.googleapis.com/v1/projects/{self.PROJECT_NUM}"
            f"/locations/global/collections/default_collection"
            f"/engines/{self.ENGINE_ID}/servingConfigs/default_search:answer"
        )
        payload = {
            "query": {"text": question},
        }

        resp = requests.post(url, headers=self._headers(), json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        answer = data.get("answer", {})
        return answer.get("answerText", "No answer generated.")
