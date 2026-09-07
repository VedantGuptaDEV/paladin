import requests

def send_prompt(prompt):
    url = "http://172.18.227.229:11434/v1/chat/completions"

    data = {
        "model": "qwen2.5",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    response = requests.post(url, json=data)
    response.raise_for_status()

    result = response.json()

    return result["choices"][0]["message"]["content"]

response = send_prompt("Explain Python decorators with examples.")
print(response)
