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

        accuracy = correct_count / total_count  # Accuracy as a fraction (0 to 1)
        return accuracy, correct_count, total_count

    def log_entry(self, prompt, response, response_time, token_usage, puzzle_name, variant, ground_truth):
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
            "total_expected": total_count
        }
        with open(LOG_FILE, "r+") as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=4)

    def read_logs(self):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
