import ast
import csv
import operator
import pathlib
import re
from _ast import expr
from typing import Callable

from parsing import save_new_data_for_testing, process_results


def receive_command(command_validator: Callable[[str], bool], hint: str) -> str:
    command = input()
    while not command_validator(command):
        print("I didn't understand you, please type: " + hint + "\n>>> ", end="")
        command = input()
    return command


def eval_math_expr(command: str) -> int | None:
    operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.USub: operator.neg}

    def _eval(node: expr) -> int:
        match node:
            case ast.Constant(val) if isinstance(val, int):
                return val
            case ast.UnaryOp(op, val) if type(op) in operators:
                return operators[type(op)](_eval(val))
            case ast.BinOp(left, op, right) if type(op) in operators:
                return operators[type(op)](_eval(left), _eval(right))
            case _:
                raise ValueError()

    try:
        return _eval(ast.parse(command, mode='eval').body)
    except ValueError:
        return None


def is_math_expr(command: str) -> bool:
    return eval_math_expr(command) is not None


def is_yes_no(command: str) -> bool:
    return command in ["y", "n"]


def is_index(size: int) -> Callable[[str], bool]:
    return lambda c: c.isdigit() and (0 < int(c) <= size)


class ConsoleApp:
    def __init__(self, data_file_path: str | None = None):
        self.data_file_path: str | None = data_file_path
        self.data: list[tuple[str, int, bool]] | None = None
        if data_file_path is not None:
            with open(self.data_file_path) as f:
                reader = csv.reader(f)
                self.data = [(row[0], int(row[1]), row[2] == "True") for row in reader]
        self.has_unsaved_changes: bool = False

    def _update_value(self, index: int, value: int):
        self.data[index] = (
            self.data[index][0],
            self.data[index][1] + value,
            self.data[index][2]
        )

    def default_processor(self, command: str) -> bool:
        print("Unknown command typed:", command)
        return True

    def process_list(self, command: str) -> bool:
        if self.data is None:
            print("Nothing to display!")
            return True
        for entry in [row for row in self.data]:
            print(entry[0] + ":", entry[1])
        return True

    def process_parse(self, command: str) -> bool:
        data = pathlib.Path("./input.txt").read_text(encoding="utf-8")
        result, error = process_results(data)
        if error is not None:
            print(error)
        print("Parsing result:", result)
        save_new_data_for_testing((error is not None) or
                                  bool(re.search(r"^Active boosters SL:", data, re.M)) or
                                  bool(re.search(r"\(PA\)\d+(?: \+ \S*?)* = \d+ SL", data)))
        print("Would you like to improve parsing result?(y/n)\n>>> ", end="")
        command = receive_command(is_yes_no, "y (edit result) or n (proceed without editing)")
        if command == "y":
            cases = [k for k in result.keys()]
            print(
                "Entering edit mode...\n"
                "When you ready to finish type: q\n"
                "Please choose entry to edit:"
            )
            for i in range(len(cases)):
                print(i + 1, "-", cases[i])
            print(">>> ", end="")
            command = ""
            while command != "q":
                command = receive_command(lambda c: c == "q" or is_index(len(cases))(c),
                                          f"number between 1 and {len(cases)} or q")
                if command == "q":
                    continue
                case = cases[int(command) - 1]
                print("Current value for", case, "=", result[case])
                print("Please input value to add:\n>>> ", end="")
                command = receive_command(is_math_expr, "valid number")
                value = eval_math_expr(command)
                print("Changing", result[case], "to", result[case] + value)
                result[case] += value
                print(
                    "Please choose entry to edit or q:\n>>> ", end=""
                )
            print("Editing result: ", result)
        if self.data is None:
            return True
        print("Would you like to add result to existing data?(y/n)\n>>> ", end="")
        command = receive_command(is_yes_no, "y (add result) or n (do not add result)")
        if command == "y":
            for k, v in result.items():
                if v == 0:
                    continue
                found = False
                for i in range(len(self.data)):
                    if self.data[i][0] == k:
                        self._update_value(i, v)
                        found = True
                        self.has_unsaved_changes = True
                        break
                if not found:
                    print("Entry with name:", k, "was not found\n"
                                                 "What would you like to do:\n"
                                                 "n - add new entry\n"
                                                 "e - assign to some other entry\n"
                                                 "i - ignore\n"
                                                 ">>> ", end="")
                    command = receive_command(lambda c: c in ["n", "e", "i"],
                                              "n (add new entry), e (choose existing) or i (ignore)")
                    match command:
                        case "i":
                            continue
                        case "n":
                            self.data.append((k, v, False))
                            self.has_unsaved_changes = True
                        case "e":
                            print("Please choose entry to edit:")
                            for i in range(len(self.data)):
                                print(i + 1, "-", self.data[i][0])
                            print(">>> ", end="")
                            command = receive_command(is_index(len(self.data)),
                                                      f"number between 1 and {len(self.data)}")
                            self._update_value(int(command) - 1, v)
        return True

    def process_edit(self, command: str) -> bool:
        if self.data is None:
            print("Nothing to edit!")
            return True
        print(
            "Please choose entry to edit:"
        )
        for i in range(len(self.data)):
            print(i + 1, "-", self.data[i][0])
        print(">>> ", end="")
        command = receive_command(is_index(len(self.data)), f"number between 1 and {len(self.data)}")
        case_index = int(command) - 1
        print("Current value for", self.data[case_index][0], "=", self.data[case_index][1])
        print("Please input value to add:\n>>> ", end="")
        command = receive_command(is_math_expr, "valid number")
        value = eval_math_expr(command)
        print("Changing", self.data[case_index][1], "to", self.data[case_index][1] + value)
        self._update_value(case_index, value)
        self.has_unsaved_changes = True
        return True

    def process_save(self, command: str) -> bool:
        if self.data is None:
            print("Nothing to save!")
            return True
        with open(self.data_file_path, "w", newline="") as f:
            writer = csv.writer(f)
            for row in self.data:
                writer.writerow([row[0], row[1], row[2]])
        self.has_unsaved_changes = False
        return True

    def handle_quit(self) -> bool:
        if self.has_unsaved_changes:
            print("There are some unsaved changes, would you like to save them?(y/n)\n>>> ", end="")
            command = receive_command(is_yes_no, "y (save changes) or n (proceed without saving)")
            if command == "y":
                self.process_save("save")
        return False

    def process_quit(self, command: str) -> bool:
        return self.handle_quit()

    def process_q(self, command: str) -> bool:
        return self.handle_quit()

    def process_command(self, command: str) -> bool:
        command_tokens = command.split(" ")
        processor: Callable[[str], bool] = getattr(self, "process_" + command_tokens[0], self.default_processor)
        return processor(command)

    def run(self):
        print(
            "Hello fellow war thunder player, happy playing! =)\n"
            "Type:\n"
            "quit, q - to quit application\n"
            "list    - to list all vehicle records\n"
        )
        if self.data is None:
            print(
                "WARNING: data file was not loaded, application working in parsing only mode"
            )
        print("\n>>> ", end="")
        command = input()
        while self.process_command(command):
            print(">>> ", end="")
            command = input()
        print(
            "Bye =("
        )


if __name__ == "__main__":
    ConsoleApp().run()
    # unittest.main()
