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

    def compare_solutions(self, llm_output, ground_truth):
        """
        Compare the LLM's JSON output to the puzzle's ground truth, field-by-field.
        Both must be shaped like:
        {
          "houses": [
            {"House": 1, "Name": "...", "Color": "...", ...},
            ...
          ]
        }
        Each "House" is a unique integer index from 1..N.
        """
        if not llm_output or "houses" not in llm_output:
            return 0, 1
        if "houses" not in ground_truth:
            return 0, 1

        llm_map = {h["House"]: h for h in llm_output["houses"]}
        gt_map  = {h["House"]: h for h in ground_truth["houses"]}

        matches = 0
        total = 0

        for house_num, gt_data in gt_map.items():
            if house_num not in llm_map:
                total += len(gt_data) - 1  # minus the House field
                continue

            llm_data = llm_map[house_num]
            for field, gt_value in gt_data.items():
                if field == "House":
                    continue
                total += 1
                llm_value = llm_data.get(field)
                if llm_value == gt_value:
                    matches += 1

        return matches, total

    def canonicalize_constraint(self, c):
        """
        Convert a constraint dict to a canonical string for set-based comparison.
        """
        ctype = c.get("type", "unknown")
        if ctype == "range":
            low = c.get("from", None)
            high = c.get("to", None)
            return f"range(from={low},to={high})"
        elif ctype == "distinct_categories":
            # We'll treat this specially. Return a marker
            return "distinct_categories"
        elif ctype == "eq":
            var1 = c["var1"]
            if "var2int" in c:
                return f"eq(var1='{var1}',var2int={c['var2int']})"
            else:
                var2 = c["var2"]
                return f"eq(var1='{var1}',var2='{var2}')"
        elif ctype == "eq_offset":
            return f"eq_offset(var1='{c['var1']}',var2='{c['var2']}',offset={c['offset']})"
        elif ctype == "neighbor":
            return f"neighbor(var1='{c['var1']}',var2='{c['var2']}')"
        else:
            return f"{ctype}({c})"

    def compare_categories(self, puzzle_cats, llm_cats):
        """
        Compare two category dicts, e.g.:
          puzzle_cats = {"colors":["Red","Blue"], ...}
          llm_cats    = {"colors":["Red","Blue"], ...}
        We'll do:
         - For each puzzle cat: +1 if LLM has it, +1 if sets match exactly
         - So each category is up to 2 points.
        """
        matches = 0
        total = 0
        puzzle_keys = set(puzzle_cats.keys())
        llm_keys    = set(llm_cats.keys())

        for cat_name in puzzle_keys:
            total += 2
            if cat_name not in llm_keys:
                continue
            # same key => +1
            matches += 1
            puzzle_set = set(puzzle_cats[cat_name])
            llm_set    = set(llm_cats[cat_name])
            if puzzle_set == llm_set:
                matches += 1
        return matches, total

    def compare_z3_data(self, puzzle_z3, llm_z3):
        """
        Compare puzzle_z3 with llm_z3. We'll do:
         1) houses_count => 1 point
         2) categories => from compare_categories
         3) constraints => set-based intersection ignoring distinct_categories
        """
        if not isinstance(llm_z3, dict):
            return 0, 1

        puzzle_houses = puzzle_z3["houses_count"]
        puzzle_cats   = puzzle_z3["categories"]
        puzzle_constr = puzzle_z3["constraints"]

        llm_houses = llm_z3.get("houses_count", None)
        llm_cats   = llm_z3.get("categories", {})
        llm_constr = llm_z3.get("constraints", [])

        matches = 0
        total = 0

        # 1) houses_count => 1 point
        total += 1
        if llm_houses == puzzle_houses:
            matches += 1

        # 2) categories
        cat_m, cat_t = self.compare_categories(puzzle_cats, llm_cats)
        matches += cat_m
        total   += cat_t

        # 3) constraints => 1 point each puzzle constraint that matches in LLM
        puzzle_set = set()
        for pc in puzzle_constr:
            cstr = self.canonicalize_constraint(pc)
            if cstr == "distinct_categories":
                # We'll skip or do partial
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

    def log_entry(self, prompt, response, response_time, token_usage, puzzle_name, variant, ground_truth):
        """
        Existing method for final puzzle solution comparison. We keep it unchanged
        except for the line where we parse response as JSON. If this is an actual
        "houses" solution, we do compare_solutions.
        If it's not, it won't match many fields, returning low accuracy.
        """
        llm_json = {}
        try:
            llm_json = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            pass

        matches, total = self.compare_solutions(llm_json, ground_truth)
        accuracy = matches / total if total > 0 else 0
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "puzzle": puzzle_name,
            "variant": variant,
            "prompt": prompt,
            "response": response,
            "response_time": response_time,
            "token_usage": token_usage,
            "accuracy": accuracy,
            "correct_fields": matches,
            "total_fields": total,
            "ground_Truth": ground_truth
        }
        with open(LOG_FILE, "r+") as f:
            logs = json.load(f)
            logs.append(entry)
            f.seek(0)
            json.dump(logs, f, indent=4)

    def log_z3_conversion(self, puzzle_name, prompt, puzzle_z3, llm_z3_dict,
                          llm_z3_solver_result, response_time, token_usage,
                          z3_solution=None):
        """
        New method that:
         1) compares puzzle_z3 with llm_z3_dict via compare_z3_data
         2) logs the solver result we get from feeding llm_z3_dict to ZebraSolver
        """
        # Compare puzzle constraints vs. LLM constraints
        c_m, c_t = self.compare_z3_data(puzzle_z3, llm_z3_dict)
        c_acc = c_m / c_t if c_t>0 else 0

        # Turn llm_z3_dict into a string for 'response'
        if isinstance(llm_z3_dict, dict):
            llm_response_str = json.dumps(llm_z3_dict)
        else:
            llm_response_str = str(llm_z3_dict)

        # log the result
        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "puzzle": puzzle_name,
            "variant": "z3_conversion",
            "prompt": prompt,
            "response": llm_response_str,
            "response_time": response_time,
            "token_usage": token_usage,
            "accuracy": c_acc,
            "correct_fields": c_m,
            "total_fields": c_t,
            "z3_solution": z3_solution,
            "llm_z3_constraints": llm_z3_dict,
            "llm_z3_solver_result": llm_z3_solver_result,
            "groundTruth_z3": puzzle_z3 
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