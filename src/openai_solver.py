import openai
import time
import os
import json
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

class OpenAISolver:
    def __init__(self):
        # Choose a model; adjust as needed
        self.model = "gpt-4o"

    def query_llm(self, prompt):
        start_time = time.time()
        retries = 3  # Maximum number of retries
        for attempt in range(retries):
            try:
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert puzzle solver. Output only valid JSON with no extra commentary."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3
                )
                # Debug: print full response for troubleshooting
                print(f"OpenAI API Response: {response}")
                llm_response = response["choices"][0]["message"]["content"]
                response_time = round(time.time() - start_time, 2)
                token_usage = response.get("usage", {}).get("total_tokens", "N/A")
                return llm_response, response_time, token_usage
            except Exception as e:
                print(f"OpenAI API error on attempt {attempt+1}: {e}")
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        print("Error: Exceeded max retries for OpenAI API.")
        return None, None, None

    def solve_puzzle(self, prompt):
        return self.query_llm(prompt)

    def convert_to_z3_format(self, prompt):
        llm_response, response_time, token_usage = self.query_llm(prompt)
        if llm_response:
            try:
                parsed_json = json.loads(llm_response)
                return parsed_json, response_time, token_usage
            except json.JSONDecodeError:
                print("Error: Could not parse OpenAI's Z3 conversion response as JSON.")
                return "Error: Could not parse OpenAI's Z3 conversion.", response_time, token_usage
        else:
            return None, response_time, token_usage
