IMAGE_PATH = "/Users/in45776242/Desktop/store_cart.png"

import ollama

response = ollama.chat(
    model='llama3.2-vision',
    messages=[{
        'role': 'user',
        'content': 'What is in this image?',
        'images': [IMAGE_PATH]
    }]
)

print(response)