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

# e.g.: python main.py puzzle_2 solve
if len(sys.argv) > 1:
    puzzle_selected = sys.argv[1]
    if puzzle_selected in puzzles:
        if len(sys.argv) > 2:
            action = sys.argv[2].lower()
    else:
        print(f"Error: Puzzle '{puzzle_selected}' not found in puzzles.json.")
        sys.exit(1)

if puzzle_selected:
    puzzles = {puzzle_selected: puzzles[puzzle_selected]}

for puzzle_name, puzzle_data in puzzles.items():
    text_description = puzzle_data["text_description"]
    puzzle_z3 = puzzle_data.get("z3_format", None)  # official constraints if present
    puzzle_ground_truth_dict = puzzle_data["ground_truth_dict"]

    print(f"\nProcessing puzzle: {puzzle_name}")
    print("-" * 50)

    do_solve = (action in ["solve", "both"])
    do_convert = (action in ["convert", "both"])

    # Set variant for logging
    if do_solve and do_convert:
        variant = "full_test"
    elif do_solve:
        variant = "solve"
    elif do_convert:
        variant = "convert"

    solve_dict_str = "N/A"
    solve_time = 0
    solve_tokens = "N/A"

    convert_constraints = "N/A"
    convert_solver_str = "N/A"
    convert_time = 0
    convert_tokens = "N/A"

    error_msg = None

    # 1) If solving: get LLM direct solution dictionary
    if do_solve:
        llm_sol_text, rtime, tokens = mistral_solver.solve_puzzle(text_description)
        if llm_sol_text:
            solve_dict_str = llm_sol_text
            solve_time = rtime
            solve_tokens = tokens
            print("\nLLM dictionary solution:\n", llm_sol_text)
        else:
            print("No LLM puzzle solution or error from API.")
            if llm_sol_text is None:
                error_msg = "LLM puzzle solution is None (API error or rate limit)."

    # 2) If converting: get LLM Z3 constraints and feed to solver
    if do_convert:
        llm_constraints, conv_time, conv_tokens = mistral_solver.convert_to_z3_format(text_description)
        if isinstance(llm_constraints, dict):
            convert_constraints = json.dumps(llm_constraints)
            convert_time = conv_time
            convert_tokens = conv_tokens
            print("\nLLM-Generated Z3 Constraints:\n", llm_constraints)
            try:
                solver_llm = ZebraSolver(llm_constraints)
                solver_result = solver_llm.solve()
                if solver_result:
                    convert_solver_str = str(solver_result)
                    print("Z3 solver result from LLM constraints:", convert_solver_str)
                else:
                    print("No solver result or puzzle unsatisfiable from LLM constraints.")
                    error_msg = error_msg or "Z3 solver returned no solution for LLM constraints."
            except Exception as e:
                error_msg = error_msg or f"Error feeding LLM constraints to solver: {str(e)}"
        else:
            print("No valid LLM constraints or error from API.")
            if llm_constraints is None:
                error_msg = error_msg or "LLM constraints is None (API error)."

    logger.log_run(
        puzzle_name=puzzle_name,
        variant=variant,
        prompt=text_description,
        puzzle_ground_truth_dict=puzzle_ground_truth_dict,
        solve_dict_str=solve_dict_str,
        solve_time=solve_time,
        solve_tokens=solve_tokens,
        convert_constraints=convert_constraints,
        convert_solver_str=convert_solver_str,
        convert_time=convert_time,
        convert_tokens=convert_tokens,
        puzzle_z3=puzzle_z3,
        error_msg=error_msg
    )

    print("\nDone. Stopping now.")
    print("=" * 50)
