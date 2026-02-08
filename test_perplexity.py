
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.getcwd())

from backend.api.perplexity import PerplexityClient

def test_client():
    load_dotenv()
    client = PerplexityClient()
    
    print("Testing PerplexityClient connection...")
    try:
        messages = [{"role": "user", "content": "Say hello in one word."}]
        response = client.chat_completion(messages)
        print("Response:", response['choices'][0]['message']['content'])
        print("SUCCESS: Client connected and received response.")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_client()
