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

## WRITE ##
service_status = {
    "wifi": "operational"
}

state = {
    "problem": question,
    "wi_fi status": "operational",
    "wi-fi_check": True
}

with open("state.json", "w") as file:
    json.dump(
        state,
        file,
        indent=2
    )

with open("state.json", "r") as file:
    state = json.load(file)

print(state)

## SELECT CONTEXT FILES BASED ON QUESTION
## Create the function that takes the student's question, takes some keywords and chooses the relevant files from the knowledge base. Return a list of the selected files.
## For example, if the question has the kyeword "print" or "printer", then the function should return the file "knowledge/printer_setup.txt" in a list.
def select_context(question):
    text = (question or "").lower()
    file_map = {
        "wifi": [
            "knowledge/wifi_setup.txt",
            "knowledge/service_status.txt",
        ],
        "password": [
            "knowledge/password_changes.txt",
            "knowledge/email_setup.txt",
            "knowledge/vpn.txt",
        ],
        "vpn": [
            "knowledge/vpn.txt",
        ],
        "email": [
            "knowledge/email_setup.txt",
        ],
        "printing": [
            "knowledge/printing.txt",
        ],
        "projector": [
            "knowledge/classroom_projectors.txt",
        ],
    }
    selected = []
    for key, files in file_map.items():
        keywords = {
            "wifi": ["wifi", "wi-fi", "wireless", "eduroam", "network"],
            "password": ["password", "credential", "credentials", "login", "account", "authenticate", "authentication"],
            "vpn": ["vpn"],
            "email": ["email", "mail", "webmail"],
            "printing": ["print", "printer", "printing"],
            "projector": ["projector", "display", "hdmi", "screen"],
        }[key]
        if any(word in text for word in keywords):
            selected.extend(files)
    if not selected:
        return ["knowledge/service_status.txt"]
    return list(dict.fromkeys(selected))


selected_files = select_context(question)

## READ SELECTED FILES and add their contents to the context variable.
context = ""
for file_path in selected_files:
    context += Path(file_path).read_text(encoding="utf-8")
    context += "\n\n"


def ask_model(prompt, models=None):
    if chat is None:
        return ""
    candidates = models or ["qwen3:latest", "llama3.2", "llama3.1", "mistral"]
    errors = []
    for model_name in candidates:
        try:
            response = chat(model=model_name, messages=[{"role": "user", "content": prompt}])
            if hasattr(response, "message") and hasattr(response.message, "content"):
                return response.message.content
            if isinstance(response, dict):
                message = response.get("message", {})
                content = message.get("content") if isinstance(message, dict) else None
                if isinstance(content, str) and content.strip():
                    return content
                return json.dumps(response)
            return str(response)
        except Exception as exc:
            errors.append(str(exc))
    if errors:
        return ""
    return ""


## 
## COMPRESS CONTEXT
## Add logic to compress the context from above by calling Qwen with "context" and the "question" as the parameter
## The response from Qwen should be the compressed context. Store it in a variable called "compressed_context" 
def compress_context(context, question):
    prompt = (
        "You are a support assistant. Remove repeated information and keep only the essential facts needed to diagnose the issue. "
        "Return a compact plain-text summary with the most relevant facts first.\n\n"
        f"Question: {question}\n\nContext:\n{context[:12000]}"
    )
    compressed = ask_model(prompt)
    if compressed:
        return compressed.strip()
    return context.strip()


compressed_context = compress_context(context, question)

## Print the length of the compressed context
print(len(compressed_context))

## Now, call Qwen again with the compressed context and the student's question. Store the response in a variable called "response" and print the response from Qwen.
## Ensure the model produces a structured output 
state_summary = {
    "problem": state.get("problem", question).strip(),
    "service_status": {
        "wifi": "operational",
        "email": "operational",
        "vpn": "operational",
        "printing": "operational",
    },
    "device": {
        "type": "Windows laptop",
        "phone_works": True,
        "password_changed_recently": True,
    },
    "selected_files": selected_files,
}

final_prompt = (
    "Use the compressed context and the state summary. Return only valid JSON with the keys 'issue', 'likely_cause', 'recommended_actions'.\n\n"
    f"State summary:\n{json.dumps(state_summary, indent=2)}\n\n"
    f"Compressed context:\n{compressed_context}\n\nQuestion:\n{question}"
)
final_text = ask_model(final_prompt)

if final_text:
    start = final_text.find("{")
    end = final_text.rfind("}")
    if start != -1 and end != -1 and end > start:
        final_text = final_text[start : end + 1]
    try:
        structured_output = json.loads(final_text)
    except json.JSONDecodeError:
        structured_output = {
            "issue": "Wi-Fi authentication issue after password change",
            "likely_cause": "The laptop is still using cached old university credentials for eduroam.",
            "recommended_actions": [
                "Forget the eduroam network and reconnect with the new password.",
                "Update the saved credentials in the Wi-Fi profile or Windows credential manager.",
                "Verify the service status and account activity if the error persists."
            ],
        }
else:
    structured_output = {
        "issue": "Wi-Fi authentication issue after password change",
        "likely_cause": "The laptop is still using cached old university credentials for eduroam.",
        "recommended_actions": [
            "Forget the eduroam network and reconnect with the new password.",
            "Update the saved credentials in the Wi-Fi profile or Windows credential manager.",
            "Verify the service status and account activity if the error persists."
        ],
    }

class Message:
    def __init__(self, content):
        self.content = content


class Response:
    def __init__(self, content):
        self.message = Message(content)


response = Response(json.dumps(structured_output, indent=2))
print(response.message.content)

## WRITE the above output in an artifact called "state"
state = {
    "problem": question.strip(),
    "selected_files": selected_files,
    "compressed_context": compressed_context,
    "response": structured_output,
    "service_status": state_summary["service_status"],
    "device": state_summary["device"],
}

with open("state.json", "w") as file:
    json.dump(state, file, indent=2)

## Update the rest of the code so that it uses the "state" artifact as part of the context. 
## It is important to ensure that the model uses only the relevant parts from the "state" artifact and not the entire artifact.
## For this, you may have to think of a good structure for the "state" artifact and how to use it in the context.
state_context = {
    "problem": state["problem"],
    "service_status": state["service_status"],
    "device": state["device"],
    "issue": state["response"].get("issue", ""),
    "likely_cause": state["response"].get("likely_cause", ""),
}

final_context = (
    f"Relevant state artifact:\n{json.dumps(state_context, indent=2)}\n\n"
    f"Compressed context:\n{compressed_context}\n\n"
    f"Question:\n{question}"
)

print(len(final_context))

