def get_prompt(mode, strategy):
    """
    Returns a prompt template based on the mode ('solve' or 'convert')
    and the chosen strategy ('baseline', 'cot', 'multishot').
    """
    if strategy == "cot":
        if mode == "solve":
            return """Think critically and show your step-by-step reasoning in the "explanation" field to solve the puzzle below. 
                        Then produce a final JSON with exactly these two fields:

                        {
                        "explanation": "...",
                        "solution": { ... }
                        }

                        **Do not** use triple-backticks or any code fences. 
                        **Do not** include any extra text outside the JSON.
                        **Do not** add Markdown headings or bullet points.
                        Your entire response must be valid JSON, period.

                    Below are the rules for solving:
                    -------------------------------------------------------------------
                    Solve this puzzle by returning a Python/JSON dictionary
                        that maps each distinct item (like colors or names) to an integer house index,
                        where House #1 is the leftmost and House #N is the rightmost. 

                    For example, if there are two items: Red, Blue for houses left to right,
                    and we know Red=1 (left), Blue=2 (right). If the puzzle also says PersonA=1, PersonB=2,
                    the final dictionary is exactly:

                    {'Red':1,'Blue':2,'PersonA':1,'PersonB':2}

                    Make sure there is No explanations, extra text or commentary in the solution key and just the dictionary in the EXACT format shown.
                    -------------------------------------------------------------------
                    Therefore, final output must be valid JSON in the form:
                    {
                    "explanation": "<chain-of-thought reasoning>",
                    "solution": {
                        "Red": 1,
                        "Blue": 2,
                        "PersonA": 1,
                        "PersonB": 2
                        ...
                    }
                    }
                    """
        elif mode == "convert":
            return """Think critically and, show your step-by-step chain-of-thought reasoning (explanation).
                    Then, produce a final JSON with two keys: "explanation" for your reasoning, and
                    "z3" for the actual constraints.

                    Below are the rules for converting puzzles to Z3:
                    -------------------------------------------------------------------
                    You are given a logic puzzle.

                    Convert this puzzle into a JSON structure usable by a Z3 solver:
                    - The JSON must have: "houses_count", "categories", and "constraints".
                    - "categories" is a dictionary mapping each category name to a list of items (strings).
                    - "constraints" is a list of objects describing each constraint. Each constraint must use exactly one of the following types:
                        - "eq"
                        - "eq_offset"
                        - "neighbor"
                        - "neq"
                        - "ImmediateLeft"
                        - "ImmediateRight"
                        - "distinct_categories"
                        - "range"
                        - "rightOf"    (means var1 is to the right of var2)
                        - "leftOf"     (means var1 is to the left of var2)
                        - "abs_diff"   (means the absolute difference between var1 and var2 equals a given number)
                        - Use only the following keys for each constraint as needed: "type", "var1", "var2", "offset", "var2int", "diff", and "categories".
                    - For "distinct_categories", ALWAYS use the format:
                        {{
                        "type":"distinct_categories",
                        "categories":["colors","names",...]
                        }}
                    Do not include "var1" or "var2" in this constraint.
                    -Include exactly one "range" constraint with keys "from" and "to".
                        For instance, if the puzzle has 5 houses, the range constraint is:
                        {
                            "type": "range",
                            "from": 1,
                            "to": 5
                        }
                        This ensures each item is an integer from 1..5.
                    - Do NOT invent new constraint types or items that aren't in the puzzle's categories.
                    - Do NOT include explanations, reasoning, or extraneous text. Only output valid JSON.
                    - If referencing a numeric house index for a 'neq' or 'eq' constraint, use 'var2int'. For example:
                    {
                        "type": "neq",
                        "var1": "X",
                        "var2int": 2
                    }
                    means X cannot equal 2.

                    Example output (dummy puzzle, not your real puzzle):
                    {
                    "houses_count": 5,
                    "categories": {
                        "colors": ["Red","Green","Blue","Yellow","White"],
                        "people": ["Alice","Bob","Charlie","Diana","Evan"]
                    },
                    "constraints": [
                        {
                        "type":"distinct_categories",
                        "categories":["colors","people"]
                        },
                        {
                        "type":"range",
                        "from":1,
                        "to":5
                        },
                        { "type":"eq","var1":"Alice","var2":"Red" },
                        { "type":"eq_offset","var1":"Blue","var2":"Green","offset":1 },
                        { "type":"neighbor","var1":"Bob","var2":"Alice" }
                    ]
                    }

                    Make sure there is No explanations, extra text or commentary in the solution key and just the dictionary in the EXACT format shown.
                    -------------------------------------------------------------------
                    Therefore, final output must be valid JSON in the form:
                    {
                    "explanation": "<chain-of-thought reasoning>",
                    "z3": {
                    "houses_count": 5,
                    "categories": {
                        "colors": ["Red","Green","Blue","Yellow","White"],
                        "people": ["Alice","Bob","Charlie","Diana","Evan"]
                    },
                    "constraints": [
                        {
                        "type":"distinct_categories",
                        "categories":["colors","people"]
                        },
                        {
                        "type":"range",
                        "from":1,
                        "to":5
                        },
                        { "type":"eq","var1":"Alice","var2":"Red" },
                        { "type":"eq_offset","var1":"Blue","var2":"Green","offset":1 },
                        { "type":"neighbor","var1":"Bob","var2":"Alice" }
                    ]
                    }
                    }
"""
    elif strategy == "multishot":
        if mode == "solve":
            return """Solve this puzzle by returning a Python/JSON dictionary
                that maps each distinct item (like colors or names) to an integer house index,
                where House #1 is the leftmost and House #N is the rightmost. No explanations
                or commentary, just the dictionary.

                For example, for this question:There are five houses. The Englishman lives in the red house. The Spaniard owns the dog. Coffee is drunk in the green house. The Ukrainian drinks tea. The green house is immediately to the right of the ivory house. The Old Gold smoker owns snails. Kools are smoked in the yellow house. Milk is drunk in the middle house. The Norwegian lives in the first house. The man who smokes Chesterfields lives in the house next to the man with the fox. Kools are smoked in the house next to the house where the horse is kept. The Lucky Strike smoker drinks orange juice. The Japanese smokes Parliaments. The Norwegian lives next to the blue house. Now, who drinks water? Who owns the zebra?
                The Solution would be: {
            "Englishman": 3,
            "Spaniard": 4,
            "Ukrainian": 2,
            "Norwegian": 1,
            "Japanese": 5,
            "Red": 3,
            "Green": 5,
            "Ivory": 4,
            "Blue": 2,
            "Yellow": 1,
            "Fox": 1,
            "Horse": 2,
            "Zebra": 5,
            "Dog": 4,
            "Snails": 3,
            "Coffee": 5,
            "Milk": 3,
            "OrangeJuice": 4,
            "Tea": 2,
            "Water": 1,
            "Parliaments": 5,
            "Kools": 1,
            "LuckyStrike": 4,
            "OldGold": 3,
            "Chesterfields": 2
        }

        For this question: There are two houses. One is red, the other is blue. Person A lives in the red house, and Person B lives in the blue house. Who lives in each house?
        The solution would be:
        {
            "Red": 1,
            "Blue": 2,
            "PersonA": 1,
            "PersonB": 2
        }

        For this question: here are 3 houses, numbered 1 to 3 from left to right. Each house is occupied by a different person. Each house has a unique attribute for each characteristic:\n- Names: Peter, Eric, Arnold\n- Drinks: tea, water, milk\n\n## Clues\n1. Peter is in the second house.\n2. Arnold is directly left of the one who only drinks water.\n3. The one who only drinks water is directly left of the person who likes milk.\n\nWe want to know who lives in each house and who drinks what.
        The solution would be: {
            "Peter": 2,
            "Eric": 3,
            "Arnold": 1,
            "tea": 1,
            "water": 2,
            "milk": 3
        }

                No extra text, just that dictionary structure.
                """
        elif mode == "convert":
            return """You are given a logic puzzle.

        Convert this puzzle into a JSON structure usable by a Z3 solver:
        - The JSON must have: "houses_count", "categories", and "constraints".
        - "categories" is a dictionary mapping each category name to a list of items (strings).
        - "constraints" is a list of objects describing each constraint. Each constraint must use exactly one of the following types:
            - "eq"
            - "eq_offset"
            - "neighbor"
            - "neq"
            - "ImmediateLeft"
            - "ImmediateRight"
            - "distinct_categories"
            - "range"
            - "rightOf"    (means var1 is to the right of var2)
            - "leftOf"     (means var1 is to the left of var2)
            - "abs_diff"   (means the absolute difference between var1 and var2 equals a given number)
            - Use only the following keys for each constraint as needed: "type", "var1", "var2", "offset", "var2int", "diff", and "categories".
        - For "distinct_categories", ALWAYS use the format:
            {{
            "type":"distinct_categories",
            "categories":["colors","names",...]
            }}
        Do not include "var1" or "var2" in this constraint.
        -Include exactly one "range" constraint with keys "from" and "to".
            For instance, if the puzzle has 5 houses, the range constraint is:
            {
                "type": "range",
                "from": 1,
                "to": 5
            }
            This ensures each item is an integer from 1..5.
        - Do NOT invent new constraint types or items that aren't in the puzzle's categories.
        - Do NOT include explanations, reasoning, or extraneous text. Only output valid JSON.
         - If referencing a numeric house index for a 'neq' or 'eq' constraint, use 'var2int'. For example:
        {
            "type": "neq",
            "var1": "X",
            "var2int": 2
        }
        means X cannot equal 2.

        For example, for this question:There are five houses. The Englishman lives in the red house. The Spaniard owns the dog. Coffee is drunk in the green house. The Ukrainian drinks tea. The green house is immediately to the right of the ivory house. The Old Gold smoker owns snails. Kools are smoked in the yellow house. Milk is drunk in the middle house. The Norwegian lives in the first house. The man who smokes Chesterfields lives in the house next to the man with the fox. Kools are smoked in the house next to the house where the horse is kept. The Lucky Strike smoker drinks orange juice. The Japanese smokes Parliaments. The Norwegian lives next to the blue house. Now, who drinks water? Who owns the zebra?
                The Solution would be: {
            "houses_count": 5,
            "categories": {
                "nationalities": ["Englishman", "Spaniard", "Ukrainian", "Norwegian", "Japanese"],
                "colors": ["Red", "Green", "Ivory", "Blue", "Yellow"],
                "pets": ["Fox", "Horse", "Zebra", "Dog", "Snails"],
                "drinks": ["Coffee", "Milk", "OrangeJuice", "Tea", "Water"],
                "cigarettes": ["Parliaments", "Kools", "LuckyStrike", "OldGold", "Chesterfields"]
            },
            "constraints": [
                {
                    "type": "distinct_categories",
                    "categories": [
                        "nationalities",
                        "colors",
                        "pets",
                        "drinks",
                        "cigarettes"
                    ]
                },
                {
                    "type": "range",
                    "from": 1,
                    "to": 5
                },
                {"type": "eq", "var1": "Englishman", "var2": "Red"},
                {"type": "eq", "var1": "Spaniard", "var2": "Dog"},
                {"type": "eq", "var1": "Coffee", "var2": "Green"},
                {"type": "eq", "var1": "Ukrainian", "var2": "Tea"},
                {"type": "eq_offset", "var1": "Green", "var2": "Ivory", "offset": 1},
                {"type": "eq", "var1": "OldGold", "var2": "Snails"},
                {"type": "eq", "var1": "Kools", "var2": "Yellow"},
                {"type": "eq", "var1": "Milk", "var2int": 3},
                {"type": "eq", "var1": "Norwegian", "var2int": 1},
                {"type": "neighbor", "var1": "Chesterfields", "var2": "Fox"},
                {"type": "neighbor", "var1": "Kools", "var2": "Horse"},
                {"type": "eq", "var1": "LuckyStrike", "var2": "OrangeJuice"},
                {"type": "eq", "var1": "Japanese", "var2": "Parliaments"},
                {"type": "neighbor", "var1": "Norwegian", "var2": "Blue"}
            ]
        }

        For this question: There are two houses. One is red, the other is blue. Person A lives in the red house, and Person B lives in the blue house. Who lives in each house?
        {
            "houses_count": 2,
            "categories": {
                "colors": ["Red", "Blue"],
                "people": ["A", "B"]
            },
            "constraints": [
                {
                    "type": "distinct_categories",
                    "categories": ["colors", "people"]
                },
                {
                    "type": "range",
                    "from": 1,
                    "to": 2
                },
                {"type": "eq", "var1": "PersonA", "var2": "Red"},
                {"type": "eq", "var1": "PersonB", "var2": "Blue"}
            ]
        }

        For this question: here are 3 houses, numbered 1 to 3 from left to right. Each house is occupied by a different person. Each house has a unique attribute for each characteristic:\n- Names: Peter, Eric, Arnold\n- Drinks: tea, water, milk\n\n## Clues\n1. Peter is in the second house.\n2. Arnold is directly left of the one who only drinks water.\n3. The one who only drinks water is directly left of the person who likes milk.\n\nWe want to know who lives in each house and who drinks what.
        The solution would be: {
            "houses_count": 3,
            "categories": {
                "names": ["Peter", "Eric", "Arnold"],
                "drinks": ["tea", "water", "milk"]
            },
            "constraints": [
                {
                    "type": "distinct_categories",
                    "categories": ["names", "drinks"]
                },
                {
                    "type": "range",
                    "from": 1,
                    "to": 3
                },
                { "type": "eq", "var1": "Peter", "var2int": 2 },
                {
                    "type": "eq_offset",
                    "var1": "water",
                    "var2": "Arnold",
                    "offset": 1
                },
                {
                    "type": "eq_offset",
                    "var1": "milk",
                    "var2": "water",
                    "offset": 1
                }
            ]
        }
        

        ONLY output valid JSON. No commentary.
        Puzzle:
        
        """
    else:
        # Fallback to baseline
        if mode == "solve":
            return """Solve this puzzle by returning a Python/JSON dictionary
                that maps each distinct item (like colors or names) to an integer house index,
                where House #1 is the leftmost and House #N is the rightmost. No explanations
                or commentary, just the dictionary.

                For example, if there are two items: Red, Blue for houses left to right,
                and we know Red=1 (left), Blue=2 (right). If the puzzle also says PersonA=1, PersonB=2,
                the final dictionary is exactly:

                {
                    "Red": 1,
                    "Blue": 2,
                    "PersonA": 1,
                    "PersonB": 2
                }

                No extra text, just that dictionary structure.
                """
        elif mode == "convert":
            return """You are given a logic puzzle.

        Convert this puzzle into a JSON structure usable by a Z3 solver:
        - The JSON must have: "houses_count", "categories", and "constraints".
        - "categories" is a dictionary mapping each category name to a list of items (strings).
        - "constraints" is a list of objects describing each constraint. Each constraint must use exactly one of the following types:
            - "eq"
            - "eq_offset"
            - "neighbor"
            - "neq"
            - "ImmediateLeft"
            - "ImmediateRight"
            - "distinct_categories"
            - "range"
            - "rightOf"    (means var1 is to the right of var2)
            - "leftOf"     (means var1 is to the left of var2)
            - "abs_diff"   (means the absolute difference between var1 and var2 equals a given number)
            - Use only the following keys for each constraint as needed: "type", "var1", "var2", "offset", "var2int", "diff", and "categories".
        - For "distinct_categories", ALWAYS use the format:
            {{
            "type":"distinct_categories",
            "categories":["colors","names",...]
            }}
        Do not include "var1" or "var2" in this constraint.
        -Include exactly one "range" constraint with keys "from" and "to".
            For instance, if the puzzle has 5 houses, the range constraint is:
            {
                "type": "range",
                "from": 1,
                "to": 5
            }
            This ensures each item is an integer from 1..5.
        - Do NOT invent new constraint types or items that aren't in the puzzle's categories.
        - Do NOT include explanations, reasoning, or extraneous text. Only output valid JSON.
         - If referencing a numeric house index for a 'neq' or 'eq' constraint, use 'var2int'. For example:
        {
            "type": "neq",
            "var1": "X",
            "var2int": 2
        }
        means X cannot equal 2.

        Example output (dummy puzzle, not your real puzzle):
        {{
        "houses_count": 5,
        "categories": {{
            "colors": ["Red","Green","Blue","Yellow","White"],
            "people": ["Alice","Bob","Charlie","Diana","Evan"]
        }},
        "constraints": [
            {{
            "type":"distinct_categories",
            "categories":["colors","people"]
            }},
            {{
            "type":"range",
            "from":1,
            "to":5
            }},
            {{ "type":"eq","var1":"Alice","var2":"Red" }},
            {{ "type":"eq_offset","var1":"Blue","var2":"Green","offset":1 }},
            {{ "type":"neighbor","var1":"Bob","var2":"Alice" }}
        ]
        }}

        ONLY output valid JSON. No commentary.
        Puzzle:
        
        """
