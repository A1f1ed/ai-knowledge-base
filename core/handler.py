from typing import List, Dict, Tuple
from langchain.schema import Document
from utils.logger import logger
from utils.api_handler import APIHandler
from utils.search_parser import parse_search_results_to_documents


def handle_free_chat(llm, user_question: str, chat_history: List[Dict]) -> Tuple[str, List[Document]]:
    """
    free chat handler: LLM direct answer → determine if search is needed → search → construct new prompt → answer
    return answer text and source documents list.
    """
    try:
        # 1. format chat history
        formatted_history = format_chat_history(chat_history)

        # 2. first LLM answer
        prompt = f"""
        {formatted_history}

        【当前问题】
        {user_question}

        📋 【answer requirements】：
        1. if you can determine the answer, please directly answer
        2. if you are uncertain, please indicate that you need to search
        """
        answer = llm.invoke(prompt)
        documents = []

        # 3. determine if search is needed
        if should_perform_search(user_question, answer):
            logger.info(f"🔍 trigger external search: {user_question}")
            api = APIHandler()
            result = api.search_web(user_question)

            if result.get("success"):
                documents = parse_search_results_to_documents(result["data"])
                search_text = format_search_docs(documents)

                enhanced_prompt = f"""
                {formatted_history}

                【current question】
                {user_question}

                【initial answer】
                {answer}

                🔍 【reference materials】：
                {search_text}

                ✅ 【please integrate these information to answer】
                """
                answer = llm.invoke(enhanced_prompt)

        return answer, documents

    except Exception as e:
        logger.error(f"free chat handler failed: {str(e)}", exc_info=True)
        return "sorry, AI cannot answer, please try again later.", []


def format_chat_history(chat_history: List[Dict]) -> str:
    if not chat_history:
        return ""
    lines = []
    for msg in chat_history[-5:]:
        role = "用户：" if msg['role'] == 'user' else "AI："
        lines.append(f"{role}{msg['content']}")
    return "\n".join(lines)


def should_perform_search(user_question: str, llm_answer: str) -> bool:
    """
    determine if search is needed. keyword method + uncertainty judgment.
    """
    time_keywords = ["now", "latest", "this year", "today", "recently"]
    topic_keywords = ["policy", "market", "price", "release", "change"]
    uncertainty_signals = ["uncertain", "suggest search", "suggest search"]

    if any(k in user_question for k in time_keywords + topic_keywords):
        return True
    if any(s in llm_answer for s in uncertainty_signals):
        return True
    return False


def format_search_docs(documents: List[Document]) -> str:
    """
    format Document object list to prompt text (can be submitted to model)
    """
    return "\n\n".join([doc.page_content for doc in documents])

__all__ = ["handle_free_chat"]