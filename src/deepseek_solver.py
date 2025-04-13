import time
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
# Initialize the DeepSeek client with the custom base_url.
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

class DeepSeekSolver:
    def __init__(self):
        # Set the model as described in the DeepSeek documentation.
        self.model = "deepseek-reasoner"

    def query_llm(self, prompt):
        start_time = time.time()
        retries = 10  # Maximum number of retries
        for attempt in range(retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert puzzle solver. Output only valid JSON with no extra commentary."},
                        {"role": "user", "content": prompt}
                    ],
                    stream=False
                )
                # Debug: print full response for troubleshooting
                print(f"DeepSeek API Response: {response}")
                llm_response = response.choices[0].message.content
                response_time = round(time.time() - start_time, 2)
                token_usage = response.usage.total_tokens if hasattr(response, 'usage') and response.usage.total_tokens is not None else "N/A"
                return llm_response, response_time, token_usage
            except Exception as e:
                print(f"DeepSeek API error on attempt {attempt+1}: {e}")
                wait_time = 2 ** attempt
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        print("Error: Exceeded max retries for DeepSeek API.")
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
                print("Error: Could not parse DeepSeek's Z3 conversion response as JSON.")
                return "Error: Could not parse DeepSeek's Z3 conversion.", response_time, token_usage
        else:
            return None, response_time, token_usage
