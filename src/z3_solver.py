from z3 import Int, Solver, Distinct

class ZebraSolver:
    def __init__(self, puzzle):
        self.solver = Solver()
        self.puzzle = puzzle
        self.variables = {var: Int(var) for var in puzzle["variables"]}

    def add_constraints(self):
        self.solver.add(Distinct([self.variables[var] for var in self.puzzle["variables"]]))

        for constraint in self.puzzle["constraints"]:
            if constraint["type"] == "eq":
                self.solver.add(self.variables[constraint["var1"]] == self.variables[constraint["var2"]])
            elif constraint["type"] == "neighbor":
                self.solver.add(abs(self.variables[constraint["var1"]] - self.variables[constraint["var2"]]) == 1)

    def solve(self):
        self.add_constraints()
        if self.solver.check() == "sat":
            model = self.solver.model()
            return {var: model[self.variables[var]] for var in self.variables}
        return None