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
            "model": "mistral-tiny",
            "messages": [
                {"role": "system", "content": "You are an expert puzzle solver. Output only the final dictionary or JSON, "
                        "with no extra commentary or explanations."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }

        retries = 3  # Max number of retries
        for attempt in range(retries):
            response = requests.post(self.url, json=data, headers=headers)
            response_json = response.json()

            # Debugging print
            print(f"Mistral API Response: {response_json}")

            # Handle rate limit errors
            if "message" in response_json and "rate limit exceeded" in response_json["message"].lower():
                wait_time = (2 ** attempt)  # Exponential backoff (2, 4, 8 sec)
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
                continue  # Retry the request

            if "choices" not in response_json:
                print("Error: Mistral API did not return 'choices'. Full response:", response_json)
                return None, None, None  # Avoid crashing, return None values

            llm_response = response_json["choices"][0]["message"]["content"]
            response_time = round(time.time() - start_time, 2)
            token_usage = response_json.get("usage", {}).get("total_tokens", "N/A")

            return llm_response, response_time, token_usage  # Return everything for logging in main.py

        print("Error: Exceeded max retries due to rate limits.")
        return None, None, None  # Return None if all retries fail

    def solve_puzzle(self, puzzle_text):
        """
        Uses LLM to solve the logic puzzle from text.
        Returns the response, response time, and token usage.
        """
        prompt = f"""Solve this puzzle by returning a Python/JSON dictionary
                that maps each distinct item (like colors or names) to an integer house index,
                where House #1 is the leftmost and House #N is the rightmost. No explanations
                or commentary, just the dictionary.

                For example, if there are two items: Red, Blue for houses left to right,
                and we know Red=1 (left), Blue=2 (right). If the puzzle also says PersonA=1, PersonB=2,
                the final dictionary is exactly:

                {{'Red':1,'Blue':2,'PersonA':1,'PersonB':2}}

                No extra text, just that dictionary structure.

                Puzzle:
                {puzzle_text}
                """
        return self.query_llm(prompt)

    def convert_to_z3_format(self, puzzle_text):
        """
        Uses LLM to convert a natural text puzzle into a Z3-compatible JSON format.
        Returns the response as a parsed dictionary (if valid JSON), response time, and token usage.
        """
        prompt = f"""You are given a logic puzzle:\n\n{puzzle_text}\n

        Convert this puzzle into a JSON structure usable by a Z3 solver:
        - The JSON must have: "houses_count", "categories", and "constraints".
        - "categories" is a dict of category_name -> list of items (strings).
        - "constraints" is a list of objects describing each constraint, strictly using:
            - "type": one of ["eq","eq_offset","neighbor","neq","left","right","distinct_categories","range"]
            - "var1","var2","offset","var2int","categories" as needed
        - For "distinct_categories", ALWAYS use the format:
            {{
            "type":"distinct_categories",
            "categories":["colors","names",...]
            }}
        Do not produce var1/var2 for distinct_categories.

        - Do NOT invent new constraint types or items that aren't in the puzzle's categories.
        - Do NOT include explanations, reasoning, or extraneous text. Only output valid JSON.

        Example output (dummy puzzle, not your real puzzle):
        {{
        "houses_count": 5,
        "categories": {{
            "colors": ["Red","Green","Blue","Yellow","White"],
            "people": ["Alice","Bob","Charlie","Diana","Evan"]
        }},
        "constraints": [
            {{
            "type":"distinct_categories",
            "categories":["colors","people"]
            }},
            {{
            "type":"range",
            "from":1,
            "to":5
            }},
            {{ "type":"eq","var1":"Alice","var2":"Red" }},
            {{ "type":"eq_offset","var1":"Blue","var2":"Green","offset":1 }},
            {{ "type":"neighbor","var1":"Bob","var2":"Alice" }}
        ]
        }}

        ONLY output valid JSON. No commentary.
        """

        llm_response, response_time, token_usage = self.query_llm(prompt)

        # Attempt to parse the response as JSON
        if llm_response:
            try:
                llm_z3_constraints = json.loads(llm_response)
            except json.JSONDecodeError:
                llm_z3_constraints = "Error: Could not parse LLM's Z3 conversion."
        else:
            llm_z3_constraints = None

        return llm_z3_constraints, response_time, token_usage
