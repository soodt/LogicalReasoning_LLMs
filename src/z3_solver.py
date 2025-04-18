from z3 import Solver, Distinct, Int, Or, sat, Abs
import json

class ZebraSolver:
    def __init__(self, puzzle):
        self.solver = Solver()
        self.houses_count = puzzle["houses_count"]
        self.categories = puzzle["categories"]
        self.constraints = puzzle["constraints"]

        self.item_vars = {}
        for cat_name, items in self.categories.items():
            for item in items:
                self.item_vars[item] = Int(item)

        self.errors = []

    def add_constraints(self):
        for c in self.constraints:
            ctype = c["type"]
            if ctype == "distinct_categories":
                if "categories" not in c:
                    self.errors.append(f"Missing 'categories' in distinct_categories: {c}")
                    continue

                cat_list = c["categories"]
                if not isinstance(cat_list, list):
                    self.errors.append(f"'categories' not a list in distinct_categories: {c}")
                    continue

                for cat_name in cat_list:
                    if cat_name not in self.categories:
                        self.errors.append(f"Unknown category '{cat_name}' in distinct_categories: {c}")
                        continue
                    cat_items = self.categories[cat_name]
                    self.solver.add(Distinct([self.item_vars[it] for it in cat_items]))

            elif ctype == "range":
                low = c.get("from")
                high = c.get("to")
                if low is None or high is None:
                    self.errors.append(f"range constraint missing 'from' or 'to': {c}")
                    continue
                for it in self.item_vars:
                    self.solver.add(self.item_vars[it] >= low, self.item_vars[it] <= high)

        for c in self.constraints:
            ctype = c["type"]
            if ctype in ("distinct_categories", "range"):
                continue

            if ctype == "eq":
                var1 = c.get("var1")
                if not var1 or var1 not in self.item_vars:
                    self.errors.append(f"eq referencing missing/unknown var1: {c}")
                    continue

                if "var2int" in c:
                    self.solver.add(self.item_vars[var1] == c["var2int"])
                else:
                    var2 = c.get("var2")
                    if not var2 or var2 not in self.item_vars:
                        self.errors.append(f"eq referencing missing/unknown var2: {c}")
                        continue
                    self.solver.add(self.item_vars[var1] == self.item_vars[var2])

            elif ctype == "eq_offset":
                var1 = c.get("var1")
                var2 = c.get("var2")
                offset = c.get("offset")
                if (not var1 or not var2 or offset is None
                        or var1 not in self.item_vars or var2 not in self.item_vars):
                    self.errors.append(f"eq_offset missing/unknown var1/var2/offset: {c}")
                    continue
                self.solver.add(self.item_vars[var1] == self.item_vars[var2] + offset)

            elif ctype == "neighbor":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"neighbor referencing unknown items: {c}")
                    continue
                self.solver.add(Or(
                    self.item_vars[var1] == self.item_vars[var2] + 1,
                    self.item_vars[var1] == self.item_vars[var2] - 1
                ))

            elif ctype == "neq":
                var1 = c.get("var1")
                var2int = c.get("var2int")
                if not var1 or var2int is None or var1 not in self.item_vars:
                    self.errors.append(f"neq referencing unknown var or missing var2int: {c}")
                    continue
                self.solver.add(self.item_vars[var1] != var2int)

            elif ctype == "ImmediateLeft":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"left referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] == self.item_vars[var2] - 1)

            elif ctype == "ImmediateRight":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"right referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] == self.item_vars[var2] + 1)
            elif ctype == "rightOf":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"gt referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] > self.item_vars[var2])

            elif ctype == "leftOf":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"lt referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] < self.item_vars[var2])

            elif ctype == "abs_diff":
                var1 = c.get("var1")
                var2 = c.get("var2")
                diff = c.get("diff")
                if not var1 or not var2 or diff is None or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"abs_diff missing/unknown var1/var2/diff: {c}")
                    continue
                self.solver.add(Abs(self.item_vars[var1] - self.item_vars[var2]) == diff)


            else:
                self.errors.append(f"Unknown constraint type '{ctype}': {c}")

    def solve(self):
        self.add_constraints()

        if self.errors:
            print("Constraint loading encountered errors:")
            for e in self.errors:
                print(f"  - {e}")
            return None

        print("Z3 Constraints Added:")
        print(self.solver)

        result = self.solver.check()
        if result == sat:
            model = self.solver.model()
            solution = {}
            for it in self.item_vars:
                solution[it] = model[self.item_vars[it]].as_long()
            return solution

        print("No solution found.")
        return None
# puzzle_6 = {
#     "houses_count": 2,
#     "categories": {
#         "names": ["Arnold", "Eric"],
#         "education": ["high school", "associate"],
#         "mothers": ["Aniya", "Holly"]
#     },
#     "constraints": [
#         {"type": "distinct_categories", "categories": ["names", "education", "mothers"]},
#         {"type": "range", "from": 1, "to": 2},
#         {"type": "eq", "var1": "associate", "var2int": 1},
#         {"type": "eq", "var1": "Holly", "var2": "Arnold"},
#         {"type": "neq", "var1": "Holly", "var2int": 2}
#     ]
# }
# # --- Main block ---
# if __name__ == "__main__":
#     print("Solving Puzzle 6 using ZebraSolver...\n")
#     solver = ZebraSolver(puzzle_6)
#     solution = solver.solve()
#     if solution is not None:
#         print("\nSolution found:")
#         print(json.dumps(solution, indent=4))
#     else:
#         print("\nNo solution could be found or there were errors.")