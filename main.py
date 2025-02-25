import csv
import pathlib
import re
from typing import Callable

from parsing import save_new_data_for_testing, process_results


class ConsoleApp:
    def __init__(self, data_file_path: str | None = None):
        self.data_file_path: str | None = data_file_path
        self.data: list[tuple[str, int, bool]] | None = None
        if data_file_path is not None:
            with open(self.data_file_path) as f:
                reader = csv.reader(f)
                self.data = [(row[0], int(row[1]), bool(row[2])) for row in reader]
        self.has_unsaved_changes: bool = False

    def default_processor(self, command: str) -> bool:
        print("Unknown command typed:", command)
        return True

    def process_list(self, command: str) -> bool:
        if self.data is None:
            print("No data to display!")
            return True
        for entry in [row for row in self.data]:
            print(entry[0] + ":", entry[1])
        return True

    def process_parse(self, command: str) -> bool:
        data = pathlib.Path("./input.txt").read_text(encoding="utf-8")
        res, error = process_results(data)
        if error is not None:
            print(error)
        print("Result:", res)
        save_new_data_for_testing((error is not None) or
                                  bool(re.search(r"^Active boosters SL:", data, re.M)) or
                                  bool(re.search(r"\(PA\)\d+(?: \+ \S*?)* = \d+ SL", data)))
        return True

    def handle_quit(self):
        if self.has_unsaved_changes:
            print("There are some unsaved changes, would you like to save them?(y/n)\n>>> ", end="")
            command = input()
            while command not in ["y", "n"]:
                print("I didn't understand you, "
                      "please type: y (save changes) or n (proceed without saving)\n>>> ", end="")
                command = input()
            if command == "y":
                pass
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
