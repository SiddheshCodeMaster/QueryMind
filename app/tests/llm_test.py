from ..llm.ollama_client import OllamaClient

client = OllamaClient()

response = client.generate("What is 2 + 2?")
print(response)
