import requests
import time
from dotenv import load_dotenv
import os
from src.logger import Logger

load_dotenv()
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

class MistralSolver:
    def __init__(self):
        self.api_key = MISTRAL_API_KEY
        self.url = "https://api.mistral.ai/v1/chat/completions"
        self.logger = Logger()

    def query_llm(self, prompt, puzzle_name, variant, ground_truth):
        start_time = time.time()
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        
        # Force structured answer format in the prompt
        data = {
            "model": "mistral-tiny",
            "messages": [
                {"role": "system", "content": "Solve this logic puzzle and output the answer in the format:\nHouse1 = X\nHouse2 = Y\n..."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        response = requests.post(self.url, json=data, headers=headers)
        end_time = time.time()

        response_json = response.json()
        llm_response = response_json["choices"][0]["message"]["content"]
        response_time = round(end_time - start_time, 2)

        # Extract token usage if available
        token_usage = response_json.get("usage", {}).get("total_tokens", "N/A")

        # Log accuracy & response
        self.logger.log_entry(prompt, llm_response, response_time, token_usage, puzzle_name, variant, ground_truth)

        return llm_response

    def solve_puzzle(self, puzzle_text, puzzle_name, ground_truth):
        return self.query_llm(puzzle_text, puzzle_name, "text_description", ground_truth)

    def convert_to_z3_format(self, puzzle_text, puzzle_name, ground_truth):
        prompt = f"""Given this Zebra Puzzle:\n\n{puzzle_text}\n\n
        Convert this puzzle into a structured format that can be used for a Z3 solver.
        Provide the output in JSON format."""
        return self.query_llm(prompt, puzzle_name, "z3_format", ground_truth)
