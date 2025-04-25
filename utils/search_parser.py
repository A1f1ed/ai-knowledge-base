from langchain.schema import Document
from typing import List, Dict

# ===================================
# search results parser
# ===================================
def parse_search_results_to_documents(results: List[Dict]) -> List[Document]:
    """
    Convert the data structure of results['data'] returned by the search engine to a list of LangChain Document objects.

    Each search result will become a Document, containing page_content and metadata.
    """
    documents = []
    for item in results:
        title = item.get("title", "no title")
        snippet = item.get("snippet", "no snippet")
        link = item.get("link", "no link")

        # organize content
        content = f"📌 {title}\n📄 snippet: {snippet}\n🔗 link: {link}"

        # create LangChain Document object
        doc = Document(
            page_content=content,
            metadata={"source": link, "title": title}
        )
        documents.append(doc)

    return documents

__all__ = ["parse_search_results_to_documents"]