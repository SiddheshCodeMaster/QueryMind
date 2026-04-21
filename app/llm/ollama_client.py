import requests


class OllamaClient:
    """
    Handles all communication with Ollama LLM.
    Optimized for speed + reliability.
    """

    def __init__(self, model="phi"):
        self.url = "http://localhost:11434/api/generate"
        self.model = model

    def generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": 100,
                        "temperature": 0,
                        "top_p": 0.9,
                    },
                },
                timeout=30,
            )

            if response.status_code != 200:
                return f"ERROR: Bad response {response.status_code}"

            data = response.json()

            # print("DEBUG FULL RESPONSE:", data)

            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            return "ERROR: Could not connect to Ollama. Is it running?"

        except requests.exceptions.Timeout:
            return "ERROR: Ollama request timed out"

        except Exception as e:
            return f"ERROR: {str(e)}"
