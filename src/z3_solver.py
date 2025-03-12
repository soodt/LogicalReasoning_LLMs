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

    def add_constraints(self):
        # 1) distinct_categories & range
        for c in self.constraints:
            if c["type"] == "distinct_categories":
                for cat_name in c["categories"]:
                    cat_items = self.categories[cat_name]
                    self.solver.add(Distinct([self.item_vars[it] for it in cat_items]))

            elif c["type"] == "range":
                low, high = c["from"], c["to"]
                for it in self.item_vars:
                    self.solver.add(self.item_vars[it] >= low, self.item_vars[it] <= high)

        # 2) eq, eq_offset, neighbor, etc.
        for c in self.constraints:
            ctype = c["type"]
            if ctype in ("distinct_categories", "range"):
                continue  # already processed

            if ctype == "eq":
                var1 = c["var1"]
                if "var2int" in c:
                    self.solver.add(self.item_vars[var1] == c["var2int"])
                else:
                    var2 = c["var2"]
                    self.solver.add(self.item_vars[var1] == self.item_vars[var2])

            elif ctype == "eq_offset":
                var1 = c["var1"]
                var2 = c["var2"]
                offset = c["offset"]
                self.solver.add(self.item_vars[var1] == self.item_vars[var2] + offset)

            elif ctype == "neighbor":
                var1 = c["var1"]
                var2 = c["var2"]
                self.solver.add(Or(
                    self.item_vars[var1] == self.item_vars[var2] + 1,
                    self.item_vars[var1] == self.item_vars[var2] - 1
                ))

    def solve(self):
        self.add_constraints()

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
