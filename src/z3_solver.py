from z3 import Solver, Distinct, Int, Or, sat

class ZebraSolver:
    def __init__(self, puzzle):
        """
        puzzle must have:
          - houses_count (int)
          - categories (dict of {category_name: list_of_items})
          - constraints (list of dicts describing constraints)
        """
        self.solver = Solver()
        self.houses_count = puzzle["houses_count"]
        self.categories = puzzle["categories"]
        self.constraints = puzzle["constraints"]
        
        # Create an Int variable for each item in each category
        self.item_vars = {}
        for cat_name, items in self.categories.items():
            for item in items:
                self.item_vars[item] = Int(item)

        # We'll store a list of errors encountered
        self.errors = []

    def add_constraints(self):
        """
        Load constraints into self.solver. We collect errors in self.errors for
        unknown or malformed constraints. We'll keep going, so we accumulate
        all possible errors.
        """

        # 1) distinct_categories & range
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

                # For each category, add a Distinct(...) statement
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

        # 2) eq, eq_offset, neighbor, neq, left, right
        for c in self.constraints:
            ctype = c["type"]
            # skip distinct_categories, range again (already processed)
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

            elif ctype == "left":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"left referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] < self.item_vars[var2])

            elif ctype == "right":
                var1 = c.get("var1")
                var2 = c.get("var2")
                if not var1 or not var2 or var1 not in self.item_vars or var2 not in self.item_vars:
                    self.errors.append(f"right referencing unknown items: {c}")
                    continue
                self.solver.add(self.item_vars[var1] > self.item_vars[var2])

            else:
                self.errors.append(f"Unknown constraint type '{ctype}': {c}")

    def solve(self):
        """
        Add constraints (collecting errors in self.errors). If no errors, run solver.check().
        If errors exist or unsatisfiable, return None.
        """
        self.add_constraints()

        if self.errors:
            print("Constraint loading encountered errors:")
            for e in self.errors:
                print(f"  - {e}")
            return None  # let caller handle it

        print("Z3 Constraints Added:")
        print(self.solver)  # for debugging

        result = self.solver.check()
        if result == sat:
            model = self.solver.model()
            solution = {}
            for it in self.item_vars:
                solution[it] = model[self.item_vars[it]].as_long()
            return solution

        print("No solution found.")
        return None
