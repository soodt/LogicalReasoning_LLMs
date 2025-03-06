import json
import sys
from src.z3_solver import ZebraSolver
from src.mistral_solver import MistralSolver
from src.logger import Logger

# Load puzzles
with open("data/puzzles.json", "r") as f:
    puzzles = json.load(f)

mistral_solver = MistralSolver()
logger = Logger()  # Initialize logger

# Check if a specific puzzle is requested from the command line
if len(sys.argv) > 1:
    selected_puzzle = sys.argv[1]  # Get puzzle name from command-line argument
    if selected_puzzle not in puzzles:
        print(f"Error: Puzzle '{selected_puzzle}' not found in puzzles.json")
        sys.exit(1)
    puzzles = {selected_puzzle: puzzles[selected_puzzle]}  # Run only the selected puzzle

for puzzle_name, puzzle_data in puzzles.items():
    text_description = puzzle_data["text_description"]
    z3_format = puzzle_data["z3_format"]
    ground_truth = puzzle_data["ground_truth"]

    print(f"\nProcessing: {puzzle_name}")
    print("-" * 50)

    # Default values in case only part of the pipeline runs
    z3_solution = None
    llm_response = None
    llm_z3_constraints = None
    llm_response_time = None
    llm_token_usage = None
    z3_conversion_time = None
    z3_token_usage = None

    # Solve using Z3 with ground truth constraints (Optional)
    if z3_format:
        zebra_solver = ZebraSolver(z3_format)
        z3_solution = zebra_solver.solve()
        print(f"Z3 without llm Solution: {z3_solution}" if z3_solution else "No Z3 solution found.")
    
    if not z3_solution:
        print(f"No solution found for {puzzle_name}.")
        print("=" * 50)
        continue

    # solution is a dict, e.g. {"Englishman": 3, "Red": 3, ...}
    # Let's group items by their house number
    houses_count = z3_format["houses_count"]

    # Create a dict: house_position -> list_of_items
    # e.g. { 3: ["Englishman", "Red"], 2: ["Dog"] ... }
    house_map = {}
    for item, position in z3_solution.items():
        house_map.setdefault(position, []).append(item)

    # Print out each house from 1..houses_count
    for h in range(1, houses_count + 1):
        if h not in house_map:
            print(f"House {h}: (nothing assigned)  -- Possibly means constraints didn't reference it")
        else:
            # Join the item names in a readable string
            items_str = ", ".join(sorted(house_map[h]))
            print(f"House {h}: {items_str}")

    print("=" * 50)


    print("\nZ3 format testing completed. Stopping program here.")
    
    if text_description:
        llm_z3_constraints, z3_conversion_time, z3_token_usage = mistral_solver.convert_to_z3_format(text_description)
        print(f"\nLLM-Generated Z3 Constraints for {puzzle_name}:")
        print(llm_z3_constraints)
        print(f"(Conversion took {z3_conversion_time} seconds, used {z3_token_usage} tokens)")

        # Try parsing if it's a string
        if isinstance(llm_z3_constraints, str):
            try:
                parsed = json.loads(llm_z3_constraints)
                print("\nParsed LLM constraints as JSON:")
                print(parsed)
            except json.JSONDecodeError:
                print("⚠️ Could not parse LLM's Z3 conversion.")
    
    print("\nDone. Stopping program now.")
    exit() 

    # # Run LLM to solve natural text puzzle (Optional)
    # if text_description:
    #     llm_response, llm_response_time, llm_token_usage = mistral_solver.solve_puzzle(text_description)
    #     print(f"LLM Response: {llm_response}")

    # # Convert natural text to Z3 constraints using LLM (Optional)
    # if text_description:
    #     llm_z3_constraints, z3_conversion_time, z3_token_usage = mistral_solver.convert_to_z3_format(text_description)
    #     print(f"LLM Converted Z3 Constraints: {llm_z3_constraints}")

    #     # Attempt to parse JSON output from LLM
    #     if isinstance(llm_z3_constraints, str):
    #         try:
    #             llm_z3_constraints = json.loads(llm_z3_constraints)
    #         except json.JSONDecodeError:
    #             llm_z3_constraints = "Error: Could not parse LLM's Z3 conversion."

    # # Solve using LLM-generated Z3 constraints (Optional)
    # if isinstance(llm_z3_constraints, dict):  # Ensure valid dictionary format
    #     zebra_solver_llm = ZebraSolver(llm_z3_constraints)
    #     z3_solution_llm = zebra_solver_llm.solve()
    #     print(f"Z3 Solution (LLM-Generated): {z3_solution_llm}" if z3_solution_llm else "No solution found using LLM-generated constraints.")
    # else:
    #     print("⚠️ LLM-generated constraints were invalid or not provided.")

    # # Log everything (only logging available data)
    # logger.log_entry(
    #     puzzle_name=puzzle_name,
    #     variant="full_test",
    #     prompt=text_description if text_description else "N/A",
    #     response=llm_response if llm_response else "N/A",
    #     response_time=llm_response_time if llm_response_time else "N/A",
    #     token_usage=llm_token_usage if llm_token_usage else "N/A",
    #     ground_truth=ground_truth if ground_truth else "N/A",
    #     z3_solution=z3_solution if z3_solution else "N/A",
    #     llm_z3_constraints=llm_z3_constraints if llm_z3_constraints else "N/A"
    # )

    print("=" * 50)
