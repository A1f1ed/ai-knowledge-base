import os
import requests
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")


class APIHandler:
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.cse_id = GOOGLE_CSE_ID
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    def search_web(self, query: str, num_results: int = 3) -> dict:
        if not self.api_key or not self.cse_id:
            print("⚠️ missing GOOGLE_API_KEY or GOOGLE_CSE_ID, skipping web search")
            return {"google": {"data": []}}

        try:
            response = requests.get(self.base_url, params={
                "key": self.api_key,
                "cx": self.cse_id,
                "q": query,
                "num": num_results
            })
            response.raise_for_status()
            results = response.json()
            return {
                "google": {
                    "data": results.get("items", [])
                }
            }
        except Exception as e:
            print(f"❌ web search failed: {str(e)}")
            return {"google": {"data": []}}