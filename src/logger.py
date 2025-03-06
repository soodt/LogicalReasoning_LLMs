import json
import os
import time

LOG_FILE = "results/log.json"

class Logger:
    def __init__(self):
        if not os.path.exists("results"):
            os.makedirs("results")
        if not os.path.exists(LOG_FILE):
            with open(LOG_FILE, "w") as f:
                json.dump([], f)  # Initialize empty log

    def compute_accuracy(self, response, ground_truth):
        """
        Checks if all expected key-value pairs exist in the LLM response.
        """
        correct_count = 0
        total_count = len(ground_truth)

        for expected_answer in ground_truth:
            if expected_answer in response:
                correct_count += 1

        accuracy = correct_count / total_count if total_count > 0 else 0 # Accuracy as a fraction (0 to 1)
        return accuracy, correct_count, total_count

    def log_entry(self, prompt, response, response_time, token_usage, puzzle_name, variant, ground_truth,z3_solution=None, llm_z3_constraints=None):
        accuracy, correct_count, total_count = self.compute_accuracy(response, ground_truth)
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "puzzle": puzzle_name,
            "variant": variant,
            "prompt": prompt,
            "response": response,
            "response_time": response_time,
            "token_usage": token_usage,
            "accuracy": accuracy,
            "correct_answers": correct_count,
            "total_expected": total_count,
            "z3_solution": z3_solution,
            "llm_z3_constraints": llm_z3_constraints
        }
        with open(LOG_FILE, "r+") as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=4)

    def read_logs(self):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
#{'houses_count': 2, 'categories': {'colors': ['Red', 'Blue'], 'people': ['A', 'B']}, 'constraints': 
            #[{'type': 'distinct_categories', 'categories': ['colors', 'people']}, {'type': 'eq', 'var1': 'A', 'var2': 'Red'}, {'type': 'eq', 'var1': 'B', 'var2': 'Blue'}]}


#3 format testing completed. Stopping program here.
# Mistral API Response: {'id': 'be5f6828588b403caa264589f12893b5', 'object': 'chat.completion', 'created': 1741294211, 'model': 'mistral-tiny', 'choices': [{'index': 0, 'message': {'role': 'assistant', 'tool_calls': None, 'content': '{\n  "houses_count": 5,\n  "categories": {\n    "people": ["A", "B"],\n    "nationalities": ["English", "Spanish"],\n    "pets": ["Dog", "Zebra"],\n    "drinks": ["Coffee", "Tea", "Water"],\n    "colors": ["Red", "Green"],\n    "smokes": ["Old Gold", "Kools", "Chesterfields", "Lucky Strike", "Parliaments"],\n    "animals": ["Fox", "Horse", "Snails"]\n  },\n  "constraints": [\n    {\n      "type": "distinct_categories",\n      "categories": ["people", "nationalities", "pets", "drinks", "colors", "smokes", "animals"]\n    },\n    {\n      "type": "range",\n      "from": 1,\n      "to": 5\n    },\n    { "type": "eq", "var1": "A", "var2": "Red" },\n    { "type": "eq_offset", "var1": "B", "var2": "Spanish" },\n    { "type": "eq_offset", "var1": "Dog", "var2": "B", "offset": 1 },\n    { "type": "eq_offset", "var1": "Coffee", "var2": "Green", "offset": 2 },\n    { "type": "eq_offset", "var1": "Tea", "var2": "A" },\n    { "type": "eq_offset", "var1": "Water", "var2": "B", "offset": 3 },\n    { "type": "eq_offset", "var1": "Green", "var2": "4", "offset": 1 },\n    { "type": "eq_offset", "var1": "Yellow", "var2": "3" },\n    { "type": "eq_offset", "var1": "Milk", "var2": "3" },\n    { "type": "eq_offset", "var1": "Ukrainian", "var2": "A" },\n    { "type": "eq_offset", "var1": "Japanese", "var2": "5" },\n    { "type": "eq_offset", "var1": "Parliaments", "var2": "5" },\n    { "type": "eq_offset", "var1": "Norwegian", "var2": "1" },\n    { "type": "eq_offset", "var1": "Blue", "var2": "2" },\n    { "type": "neighbor", "var1": "B", "var2": "A" },\n    { "type": "neighbor_offset", "var1": "Kools", "var2": "3", "offset": 1 },\n    { "type": "neighbor_offset", "var1": "Kools", "var2": "Yellow", "offset": 1 },\n    { "type": "neighbor_offset", "var1": "Chesterfields", "var2": "A", "offset": 1 },\n    { "type": "neighbor_offset", "var1": "Lucky Strike", "var2": "Orange Juice" },\n    { "type": "neighbor_offset", "var1": "Old Gold", "var2": "Snails" }\n  ]\n}'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 618, 'total_tokens': 1433, 'completion_tokens': 815}}

# LLM-Generated Z3 Constraints for puzzle_1:
# {'houses_count': 5, 'categories': {'people': ['A', 'B'], 'nationalities': ['English', 'Spanish'], 'pets': ['Dog', 'Zebra'], 'drinks': ['Coffee', 'Tea', 'Water'], 'colors': ['Red', 'Green'], 'smokes': ['Old Gold', 'Kools', 'Chesterfields', 'Lucky Strike', 'Parliaments'], 'animals': ['Fox', 'Horse', 'Snails']}, 'constraints': [{'type': 'distinct_categories', 'categories': ['people', 'nationalities', 'pets', 'drinks', 'colors', 'smokes', 'animals']}, {'type': 'range', 'from': 1, 'to': 5}, {'type': 'eq', 'var1': 'A', 'var2': 'Red'}, {'type': 'eq_offset', 'var1': 'B', 'var2': 'Spanish'}, {'type': 'eq_offset', 'var1': 'Dog', 'var2': 'B', 'offset': 1}, {'type': 'eq_offset', 'var1': 'Coffee', 'var2': 'Green', 'offset': 2}, {'type': 'eq_offset', 'var1': 'Tea', 'var2': 'A'}, {'type': 'eq_offset', 'var1': 'Water', 'var2': 'B', 'offset': 3}, {'type': 'eq_offset', 'var1': 'Green', 'var2': '4', 'offset': 1}, {'type': 'eq_offset', 'var1': 'Yellow', 'var2': '3'}, {'type': 'eq_offset', 'var1': 'Milk', 'var2': '3'}, {'type': 'eq_offset', 'var1': 'Ukrainian', 'var2': 'A'}, {'type': 'eq_offset', 'var1': 'Japanese', 'var2': '5'}, {'type': 'eq_offset', 'var1': 'Parliaments', 'var2': '5'}, {'type': 'eq_offset', 'var1': 'Norwegian', 'var2': '1'}, {'type': 'eq_offset', 'var1': 'Blue', 'var2': '2'}, {'type': 'neighbor', 'var1': 'B', 'var2': 'A'}, {'type': 'neighbor_offset', 'var1': 'Kools', 'var2': '3', 'offset': 1}, {'type': 'neighbor_offset', 'var1': 'Kools', 'var2': 'Yellow', 'offset': 1}, {'type': 'neighbor_offset', 'var1': 'Chesterfields', 'var2': 'A', 'offset': 1}, {'type': 'neighbor_offset', 'var1': 'Lucky Strike', 'var2': 'Orange Juice'}, {'type': 'neighbor_offset', 'var1': 'Old Gold', 'var2': 'Snails'}]}
# (Conversion took 6.46 seconds, used 1433 tokens)

# LLM-Generated Z3 Constraints for puzzle_3:
# {'houses_count': 3, 'categories': {'people': ['Peter', 'Eric', 'Arnold'], 'drinks': ['tea', 'water', 'milk']}, 'constraints': [{'type': 'distinct_categories', 'categories': ['people', 'drinks']}, {'type': 'range', 'from': 1, 'to': 3}, {'type': 'eq', 'var1': 'Peter', 'var2': '2'}, {'type': 'eq', 'var1': 'Eric', 'var2': '1'}, {'type': 'eq', 'var1': 'Arnold', 'var2': '3'}, {'type': 'eq', 'var1': 'Peter', 'var2': 'drinks[1]'}, {'type': 'eq', 'var1': 'Eric', 'var2': 'drinks[0]'}, {'type': 'eq', 'var1': 'Arnold', 'var2': 'drinks[2]'}, {'type': 'neighbor', 'var1': 'Arnold', 'var2': 'drinks[1]'}, {'type': 'neighbor', 'var1': 'drinks[1]', 'var2': 'drinks[2]'}]}
# (Conversion took 3.64 seconds, used 988 tokens)