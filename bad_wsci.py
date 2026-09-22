## This file is a bad way of managing context. 

from pathlib import Path
import json

try:
    from ollama import chat
except ImportError:
    chat = None


question = """
I changed my university password this morning.
Now my Windows laptop won't connect to campus Wi-Fi,
but my phone still works.
"""


context = ""

for file in Path("knowledge").glob("*.txt"):
    context += file.read_text(encoding="utf-8")
    context += "\n\n"


def ask_model(prompt, model_name="qwen3:latest"):
    if chat is None:
        return {
            "issue": "Wi-Fi authentication issue after password change",
            "likely_cause": "The laptop still has cached old credentials for eduroam.",
            "recommended_actions": [
                "Forget the eduroam network and reconnect with the new password.",
                "Update saved Wi-Fi credentials in Windows.",
                "Check account status if the issue continues."
            ]
        }
    response = chat(model=model_name, messages=[{"role": "user", "content": prompt}])
    if hasattr(response, "message") and hasattr(response.message, "content"):
        return response.message.content
    if isinstance(response, dict):
        return response
    return str(response)


response = ask_model(
    f"Answer the question using the knowledge context.\n\nQuestion: {question}\n\nContext:\n{context}"
)

print(
    "Context characters:",
    len(context)
)
print(response if isinstance(response, str) else json.dumps(response, indent=2))
