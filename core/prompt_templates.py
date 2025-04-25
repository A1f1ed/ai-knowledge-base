def get_free_chat_prompt(history: str, question: str, draft: str = None) -> str:
    return f"""
【history】
{history}

【current question】
{question}

【answer requirements】：
1. if you can determine the answer, please directly answer
2. if the question involves latest information (e.g., "now", "this year", "recently"), please directly say: "please query the latest data"
3. if you are uncertain, please say: "I am uncertain, please query the latest information"
4. do not fabricate information
{f"5. initial answer: {draft}" if draft else ""}
""".strip()

def get_document_chat_prompt(context: str, question: str) -> str:
    return f"""
【document context】
{context}

【current question】
{question}

【answer requirements】：
1. please strictly answer based on the document content
2. if you cannot find the content, please directly say: "the document does not mention this content"
3. do not fabricate information
""".strip()

def get_knowledge_chat_prompt(context: str, question: str) -> str:
    return f"""
【knowledge content】
{context}

【current question】
{question}

【answer requirements】：
1. please answer based on the above content
2. you can combine multiple documents or category examples
3. if there is no relevant information, please say: "no relevant information found in the knowledge"
""".strip()
