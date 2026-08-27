from langchain_ollama import ChatOllama
from parking_agent_system.config import settings

model = settings.ollama_chat_model

class ParkingChatAgent:
    def __init__(self):
        self.llm = ChatOllama(
            model=settings.ollama_chat_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )

    def generate_response(self, messages: list[dict[str, str]]) -> str:
        """
        Send messages to the local Ollama model and return the generated response text.
        """
        response = self.llm.invoke(messages)
        content = response.content

        if not isinstance(content, str):
            raise RuntimeError("The language model returned unsupported response content: {}".format(type(content)))
        
        cleaned_content = content.strip()

        if not cleaned_content:
            raise RuntimeError("The language model returned an empty response.")

        return cleaned_content