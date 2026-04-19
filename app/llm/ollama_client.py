import requests


class OllamaClient:
    def __init__(self, model="phi"):
        self.url = "http://localhost:11434/api/generate"
        self.model = model

    def generate(self, prompt):
        try:
            response = requests.post(
                self.url, json={"model": self.model, "prompt": prompt, "stream": False}
            )

            data = response.json()
            return data.get("response", "")

        except Exception as e:
            return f"ERROR: {str(e)}"
