import json
from src.z3_solver import ZebraSolver
from src.mistral_solver import MistralSolver

with open("data/puzzles.json", "r") as f:
    puzzles = json.load(f)

mistral_solver = MistralSolver()

for puzzle_name, puzzle_data in puzzles.items():
    text_description = puzzle_data["text_description"]
    z3_format = puzzle_data["z3_format"]
    ground_truth = puzzle_data["ground_truth"]

    # Run LLM on natural text
    mistral_solver.solve_puzzle(text_description, puzzle_name, ground_truth)

    # Run LLM on Z3 conversion
    mistral_solver.convert_to_z3_format(text_description, puzzle_name, ground_truth)
