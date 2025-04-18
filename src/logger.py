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
                json.dump([], f)

    def compare_dict_solution(self, llm_sol, puzzle_sol):
        if not isinstance(llm_sol, dict) or not isinstance(puzzle_sol, dict):
            return 0, 1
        matches = 0
        total = len(puzzle_sol)
        for k, v in puzzle_sol.items():
            if k in llm_sol and llm_sol[k] == v:
                matches += 1
        return matches, total

    def canonicalize_constraint(self, c):
        ctype = c.get("type", "unknown")
        if ctype == "range":
            low = c.get("from", None)
            high = c.get("to", None)
            return f"range(from={low},to={high})"
        elif ctype == "distinct_categories":
            return "distinct_categories"
        elif ctype == "eq":
            var1 = c["var1"]
            if "var2int" in c:
                return f"eq(var1='{var1}',var2int={c['var2int']})"
            else:
                var2 = c["var2"]
                return f"eq(var1='{var1}',var2='{var2}')"
        elif ctype == "eq_offset":
            return f"eq_offset(var1='{c.get('var1')}',var2='{c.get('var2')}',offset={c.get('offset')})"
        elif ctype == "neighbor":
            return f"neighbor(var1='{c.get('var1')}',var2='{c.get('var2')}')"
        elif ctype in ("left", "right"):
            return f"{ctype}(var1='{c.get('var1')}',var2='{c.get('var2')}')"
        else:
            return f"{ctype}({c})"

    def compare_categories(self, puzzle_cats, llm_cats):
        matches = 0
        total = 0
        puzzle_keys = set(puzzle_cats.keys())
        llm_keys = set(llm_cats.keys())

        for cat_name in puzzle_keys:
            total += 2
            if cat_name not in llm_keys:
                continue
            # matched key gives +1
            matches += 1
            if set(puzzle_cats[cat_name]) == set(llm_cats[cat_name]):
                matches += 1
        return matches, total

    def compare_z3_data(self, puzzle_z3, llm_z3):
        if not isinstance(llm_z3, dict):
            return 0, 1

        puzzle_houses = puzzle_z3["houses_count"]
        puzzle_cats = puzzle_z3["categories"]
        puzzle_constr = puzzle_z3["constraints"]

        llm_houses = llm_z3.get("houses_count", None)
        llm_cats = llm_z3.get("categories", {})
        llm_constr = llm_z3.get("constraints", [])

        matches = 0
        total = 0

        # Compare houses_count
        total += 1
        if llm_houses == puzzle_houses:
            matches += 1

        # Compare categories
        cat_m, cat_t = self.compare_categories(puzzle_cats, llm_cats)
        matches += cat_m
        total += cat_t

        puzzle_set = set()
        for pc in puzzle_constr:
            cstr = self.canonicalize_constraint(pc)
            if cstr == "distinct_categories":
                continue
            puzzle_set.add(cstr)

        llm_set = set()
        for lc in llm_constr:
            cstr_llm = self.canonicalize_constraint(lc)
            if cstr_llm == "distinct_categories":
                continue
            llm_set.add(cstr_llm)

        total += len(puzzle_set)
        for cstr in puzzle_set:
            if cstr in llm_set:
                matches += 1

        return matches, total

    def log_run(
        self,
        llm_provider,
        puzzle_name,
        puzzle_size,
        variant,
        strategy,
        chain_of_thought,
        prompt,
        puzzle_ground_truth_dict,
        solve_dict_str,
        solve_time,
        solve_tokens,
        convert_constraints,
        convert_solver_str,
        convert_time,
        convert_tokens,
        puzzle_z3=None,
        error_msg=None
    ):
        if solve_dict_str == "N/A":
            direct_sol_acc = 0.0
            direct_sol_correct = 0
            direct_sol_total = 1
            direct_sol_parsed = "N/A"
        else:
            try:
                parse_text = solve_dict_str.replace("'", "\"")
                direct_sol_parsed = json.loads(parse_text)
            except Exception as e:
                direct_sol_parsed = f"Parse error: {str(e)}"
                direct_sol_acc = 0.0
                direct_sol_correct = 0
                direct_sol_total = 1
                error_msg = (error_msg + " | " if error_msg else "") + f"Error parsing solve_dict_str: {str(e)}"
            else:
                m1, t1 = self.compare_dict_solution(direct_sol_parsed, puzzle_ground_truth_dict)
                direct_sol_acc = m1 / t1 if t1 > 0 else 0
                direct_sol_correct = m1
                direct_sol_total = t1

        if convert_solver_str == "N/A":
            convert_sol_acc = 0.0
            convert_sol_correct = 0
            convert_sol_total = len(puzzle_ground_truth_dict)
            convert_sol_parsed = "N/A"
        else:
            try:
                parse_text = convert_solver_str.replace("'", "\"")
                convert_sol_parsed = json.loads(parse_text)
            except Exception as e:
                convert_sol_parsed = f"Parse error: {str(e)}"
                convert_sol_acc = 0.0
                convert_sol_correct = 0
                convert_sol_total = len(puzzle_ground_truth_dict)
                error_msg = (error_msg + " | " if error_msg else "") + f"Error parsing convert_solver_str: {str(e)}"
            else:
                m2, t2 = self.compare_dict_solution(convert_sol_parsed, puzzle_ground_truth_dict)
                convert_sol_acc = m2 / t2 if t2 > 0 else 0
                convert_sol_correct = m2
                convert_sol_total = len(puzzle_ground_truth_dict)

        if puzzle_z3 and convert_constraints != "N/A":
            try:
                constraints_parsed = json.loads(convert_constraints)
            except Exception as e:
                constraints_parsed = f"Parse error: {str(e)}"
                c_m, c_t = 0, 1
                constraints_acc = 0.0
                error_msg = (error_msg + " | " if error_msg else "") + f"Error parsing convert_constraints: {str(e)}"
            else:
                c_m, c_t = self.compare_z3_data(puzzle_z3, constraints_parsed)
                constraints_acc = c_m / c_t if c_t > 0 else 0
        else:
            c_m, c_t = 0, 1
            constraints_acc = 0.0

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "llm_provider": llm_provider,
            "puzzle": puzzle_name,
            "puzzle_size": puzzle_size, 
            "variant": variant,
            "strategy": strategy,
            "chain_of_thought": chain_of_thought, 
            "prompt": prompt,
            "puzzle_ground_truth_dict": puzzle_ground_truth_dict,
            # Direct solution logging
            "solve_dict_str": solve_dict_str,
            "solve_response_time": solve_time,
            "solve_token_usage": solve_tokens,
            "solve_accuracy": direct_sol_acc,
            "solve_correct_fields": direct_sol_correct,
            "solve_total_fields": direct_sol_total,
            "solve_parsed": direct_sol_parsed,
            # Conversion logging
            "convert_constraints": convert_constraints,
            "convert_response_time": convert_time,
            "convert_token_usage": convert_tokens,
            "convert_solver_str": convert_solver_str,
            "convert_solver_accuracy": convert_sol_acc,
            "convert_correct_fields": convert_sol_correct,
            "convert_total_fields": convert_sol_total,
            "convert_solver_parsed": convert_sol_parsed,
            # Official constraints (if provided)
            "official_z3_constraints_present": bool(puzzle_z3),
            "constraints_accuracy": constraints_acc,
            "constraints_correct_fields": c_m,
            "constraints_total_fields": c_t,
            "error": error_msg if error_msg else "N/A"
        }

        with open(LOG_FILE, "r+") as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=4)

    def read_logs(self):
        with open(LOG_FILE, "r") as f:
            return json.load(f)
