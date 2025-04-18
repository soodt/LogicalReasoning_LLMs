import requests
import time
from dotenv import load_dotenv
import os
import json

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

class MistralSolver:
    def __init__(self):
        self.api_key = MISTRAL_API_KEY
        self.url = "https://api.mistral.ai/v1/chat/completions"

    def query_llm(self, prompt):
        start_time = time.time()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": "You are an expert puzzle solver. Output only the final dictionary or JSON, "
                        "with no extra commentary or explanations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        retries = 10 
        for attempt in range(retries):
            response = requests.post(self.url, json=data, headers=headers)
            response_json = response.json()

            # Debugging print
            print(f"Mistral API Response: {response_json}")

            # Handle rate limit errors
            if "message" in response_json and "rate limit exceeded" in response_json["message"].lower():
                wait_time = (2 ** attempt)
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue

            if "choices" not in response_json:
                print("Error: Mistral API did not return 'choices'. Full response:", response_json)
                return None, None, None

            llm_response = response_json["choices"][0]["message"]["content"]
            response_time = round(time.time() - start_time, 2)
            token_usage = response_json.get("usage", {}).get("total_tokens", "N/A")

            return llm_response, response_time, token_usage

        print("Error: Exceeded max retries due to rate limits.")
        return None, None, None

    def solve_puzzle(self, prompt):
        return self.query_llm(prompt)

    def convert_to_z3_format(self, prompt):

        llm_response, response_time, token_usage = self.query_llm(prompt)

        if llm_response:
            try:
                llm_z3_constraints = json.loads(llm_response)
            except json.JSONDecodeError:
                llm_z3_constraints = "Error: Could not parse LLM's Z3 conversion."
        else:
            llm_z3_constraints = None

        return llm_z3_constraints, response_time, token_usage
