import json
import sys
from src.z3_solver import ZebraSolver
from src.mistral_solver import MistralSolver
from src.logger import Logger

with open("data/puzzles.json", "r") as f:
    puzzles = json.load(f)

mistral_solver = MistralSolver()
logger = Logger()

action = "both"
puzzle_selected = None

if len(sys.argv) > 1:
    puzzle_selected = sys.argv[1]
    if puzzle_selected in puzzles:
        if len(sys.argv) > 2:
            action = sys.argv[2].lower()
    else:
        print(f"Error: Puzzle '{puzzle_selected}' not found in puzzles.json")
        sys.exit(1)

if puzzle_selected:
    puzzles = {puzzle_selected: puzzles[puzzle_selected]}

for puzzle_name, puzzle_data in puzzles.items():
    text_description = puzzle_data["text_description"]
    z3_format = puzzle_data["z3_format"]
    ground_truth = puzzle_data["ground_truth"]

    print(f"\nProcessing puzzle: {puzzle_name}")
    print("-" * 50)

    z3_solution = None
    if z3_format:
        solver = ZebraSolver(z3_format)
        z3_solution = solver.solve()
        if z3_solution:
            print("Z3 numeric assignment:", z3_solution)
        else:
            print(f"No Z3 solution found for {puzzle_name}.")
    else:
        print(f"No z3_format for puzzle: {puzzle_name}")

    do_solve = (action in ["solve","both"])
    do_convert = (action in ["convert","both"])

    llm_response = ""
    llm_response_time = 0
    llm_token_usage = "N/A"
    llm_z3_constraints = None
    z3_conversion_time = 0
    z3_token_usage = "N/A"

    # If user wants the LLM to solve in "houses" format
    if do_solve:
        sol_text, rtime, tokens = mistral_solver.solve_puzzle(text_description)
        if sol_text:
            llm_response = sol_text
            llm_response_time = rtime
            llm_token_usage = tokens
            print("\nLLM Solve JSON:\n", sol_text)
        else:
            print("No LLM puzzle solution or error from API.")
        logger.log_entry(
        prompt=text_description,
        response=llm_response,
        response_time=llm_response_time,
        token_usage=llm_token_usage,
        puzzle_name=puzzle_name,
        variant="full_test",
        ground_truth=ground_truth
    )

    # If user wants the LLM to convert puzzle => Z3 constraints
    llm_z3_solver_result = None
    if do_convert:
        conv_dict, conv_time, conv_tokens = mistral_solver.convert_to_z3_format(text_description)
        llm_z3_constraints = conv_dict
        z3_conversion_time = conv_time
        z3_token_usage = conv_tokens
        if llm_z3_constraints and isinstance(llm_z3_constraints, dict):
            print("\nLLM-Generated Z3 Constraints:")
            print(llm_z3_constraints)

            # Feed LLM constraints to a solver
            solver_llm = ZebraSolver(llm_z3_constraints)
            llm_z3_solver_result = solver_llm.solve()
            print("Z3 solution from LLM constraints:", llm_z3_solver_result)
        else:
            print("No LLM constraints or error from API.")

    # If we only do convert (and not solve), we want a valid JSON in llm_response
    if not do_solve and do_convert:
        if isinstance(llm_z3_constraints, dict):
            llm_response = json.dumps(llm_z3_constraints)
        else:
            llm_response = "{}"

    # If we did a conversion, log that separately with log_z3_conversion
    if do_convert:
        logger.log_z3_conversion(
            puzzle_name=puzzle_name,
            prompt=text_description,
            puzzle_z3=z3_format,
            llm_z3_dict=llm_z3_constraints,
            llm_z3_solver_result=llm_z3_solver_result,
            response_time=z3_conversion_time,
            token_usage=z3_token_usage,
            z3_solution=z3_solution
        )

    print("\nDone. Stopping program now.")
    print("=" * 50)
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
