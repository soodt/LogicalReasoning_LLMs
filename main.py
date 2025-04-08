import json
import sys
from src.z3_solver import ZebraSolver
from src.mistral_solver import MistralSolver
from src.logger import Logger
from src.prompt_generator import get_prompt
import argparse
from src.openai_solver import OpenAISolver
from src.deepseek_solver import DeepSeekSolver

def parse_args():
    parser = argparse.ArgumentParser(description="Solve or convert puzzles with an optional puzzle, action, and strategy.")
    parser.add_argument("--puzzle", type=str, default=None,
                        help="Puzzle key from puzzles.json. If not provided, runs for ALL puzzles.")
    parser.add_argument("--action", choices=["solve", "convert", "both"], default="both",
                        help="What to do: 'solve', 'convert', or 'both'. Default=both.")
    parser.add_argument("--strategy", choices=["baseline", "cot", "multishot"], default="baseline",
                        help="Prompt strategy. Default=baseline.")
    parser.add_argument("--llm", choices=["mistral", "openai", "deepseek"], default="mistral",
                        help="Which LLM to use: 'mistral', 'openai' or 'deepseek'. Default=mistral.")
    return parser.parse_args()

def clean_response(text):
    # Remove any leading/trailing whitespace
    text = text.strip()
    # If the text starts with a code fence (and possibly a language hint), remove those lines.
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove the first line if it starts with ```
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove the last line if it starts with ```
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()

def main():
    args = parse_args()
    
    # Load puzzles
    with open("data/puzzles.json", "r") as f:
        puzzles_dict = json.load(f)

    # If puzzle is specified, run just that puzzle. Otherwise run them all
    if args.puzzle is not None:
        if args.puzzle not in puzzles_dict:
            print(f"Error: Puzzle '{args.puzzle}' not found in puzzles.json.")
            sys.exit(1)
        puzzles = {args.puzzle: puzzles_dict[args.puzzle]}
    else:
        puzzles = puzzles_dict

    # The rest is your existing logic:
    puzzle_selected = args.puzzle
    action = args.action.lower()        # solve, convert, or both
    strategy = args.strategy.lower()    # baseline, cot, or multishot

    print(f"Running puzzle(s): {puzzle_selected if puzzle_selected else 'ALL'}")
    print(f"Action: {action}")
    print(f"Strategy: {strategy}")
    print(f"LLM Provider: {args.llm}")

    if args.llm == "openai":
        llm_solver = OpenAISolver()
    elif args.llm == "deepseek":
        llm_solver = DeepSeekSolver()
    else:
        llm_solver = MistralSolver()
    
    logger = Logger()

    for puzzle_name, puzzle_data in puzzles.items():
        text_description = puzzle_data["text_description"]
        puzzle_z3 = puzzle_data.get("z3_format", None)
        puzzle_ground_truth_dict = puzzle_data["ground_truth_dict"]
        puzzle_size = puzzle_data["size"]

        print(f"\nProcessing puzzle: {puzzle_name}")
        print("-" * 50)

        do_solve = (action in ["solve", "both"])
        do_convert = (action in ["convert", "both"])

        if do_solve and do_convert:
            variant = "full_test"
        elif do_solve:
            variant = "solve"
        elif do_convert:
            variant = "convert"
        else:
            variant = "unknown"

        solve_dict_str = "N/A"
        solve_time = 0
        solve_tokens = "N/A"

        convert_constraints = "N/A"
        convert_solver_str = "N/A"
        convert_time = 0
        convert_tokens = "N/A"

        error_msg = None
        chain_of_thought_solve = "N/A"
        chain_of_thought_convert = "N/A"

        # 1) If solving: get direct solution using the chosen prompt strategy.
        if do_solve:
            prompt_solve = get_prompt("solve", strategy) + "\n" + text_description
            llm_sol_text, rtime, tokens = llm_solver.query_llm(prompt_solve)
            if llm_sol_text:
                cleaned_text = clean_response(llm_sol_text)
                solve_dict_str = cleaned_text
                solve_time = rtime
                solve_tokens = tokens
                print("Cleaned response for solve:", cleaned_text)
                print("\nLLM dictionary solution:\n", llm_sol_text)
                if strategy == "cot":
                    try:
                        sol_obj = json.loads(cleaned_text)
                        chain_of_thought_solve = sol_obj.get("explanation", "N/A")
                        if "solution" in sol_obj:
                            # keep it as JSON string for logging
                            solve_dict_str = json.dumps(sol_obj["solution"])
                    except Exception as e:
                        print("Error parsing CoT response for puzzle solve:", e)
            else:
                print("No LLM puzzle solution or error from API.")
                if cleaned_text is None:
                    error_msg = "LLM puzzle solution is None (API error or rate limit)."

        # 2) If converting: get Z3 constraints using the chosen prompt strategy and feed them to the solver.
        if do_convert:
            prompt_convert = get_prompt("convert", strategy) + "\n" + text_description
            llm_constraints_str, conv_time, conv_tokens = llm_solver.query_llm(prompt_convert)
            if llm_constraints_str:
                convert_time = conv_time
                convert_tokens = conv_tokens
                cleaned_constraints = clean_response(llm_constraints_str)
                # If user chose "cot" for convert, expect {"explanation":..., "z3":...}
                if strategy == "cot":
                    try:
                        constraints_obj = json.loads(cleaned_constraints)
                        chain_of_thought_convert = constraints_obj.get("explanation", "N/A")
                        z3_obj = constraints_obj.get("z3", {})
                        convert_constraints = json.dumps(z3_obj)
                    except Exception as e:
                        print(f"Error parsing CoT convert response: {e}")
                        # fallback: store the raw text
                        convert_constraints = cleaned_constraints
                else:
                    # baseline or multishot: assume direct JSON of constraints
                    convert_constraints = cleaned_constraints

                try:
                    # Parse the final constraints as JSON for the solver
                    llm_constraints_json = json.loads(convert_constraints)
                    print("\nLLM-Generated Z3 Constraints:\n", llm_constraints_json)
                    try:
                        solver_llm = ZebraSolver(llm_constraints_json)
                        solver_result = solver_llm.solve()
                        if solver_result:
                            convert_solver_str = json.dumps(solver_result)
                            print("Z3 solver result from LLM constraints:", solver_result)
                        else:
                            print("No solver result or puzzle unsatisfiable from LLM constraints.")
                            error_msg = error_msg or "Z3 solver returned no solution for LLM constraints."
                    except Exception as e:
                        error_msg = error_msg or f"Error feeding LLM constraints to solver: {str(e)}"
                except Exception as e:
                    print("Error: Could not parse LLM constraints as JSON.", str(e))
                    error_msg = error_msg or f"Error parsing LLM constraints: {str(e)}"
            else:
                print("No valid LLM constraints or error from API.")
                if cleaned_constraints is None:
                    error_msg = error_msg or "LLM constraints is None (API error)."

        print(chain_of_thought_solve+chain_of_thought_convert)
        combined_chain_of_thought = "Solve: " + chain_of_thought_solve + "; Convert: " + chain_of_thought_convert

        logger.log_run(
            llm_provider=args.llm,
            puzzle_name=puzzle_name,
            puzzle_size=puzzle_size,
            variant=variant,
            strategy=strategy,
            chain_of_thought=combined_chain_of_thought,
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

if __name__ == "__main__":
    main()