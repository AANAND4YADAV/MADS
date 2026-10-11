import ollama

MODEL = "gpt-oss:120b-cloud"

def generate(prompt: str) -> str:
    response = ollama.generate(model=MODEL, prompt=prompt)
    return response["response"]
