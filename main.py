import decimal
import pathlib
import re
import unittest
from functools import reduce

decimal.getcontext().prec = 15
decimal10 = decimal.Decimal("10")

general_awards = [
    "Mission Maker",
    "Hero of the Sky",
    "Heavy Metal Hero",
    "Thunderer",
    "Tsunami",
    "Terror of the Sea",
    "Survivor",
    "Punisher",
    "Wingman",

    "The last man standing!",
    "The Best Squad",
    "Doomsday!",
    "One minute to midnight",
    "The end is near",
    "Peaceful atom",

    "Bombers' Nightmare",
    "Fighters' Nightmare",

    "Wing Breaker",

    "On Hand",
    "Balancer",
    "Rogue Wave",
    "Antimech",
    "Terror of the Sky",
    "Heavy Metal Fury",
    "Terror of the Ocean",
    "Bulletproof",
]


def get_victory_status(line: str) -> bool:
    return re.match(r"\w+", line)[0] == "Victory"


def get_reward_value(line: str) -> int:
    reward = re.search(r"\d+ SL", line)
    return int(reward[0].split(" ")[0]) if reward else 0


def get_time_in_seconds(line: str) -> int:
    time_tokens = line.split(":")
    return int(time_tokens[1]) + int(time_tokens[0]) * 60  # !!! Not likely but can be hours also


def process_played_vehicles(data: str, result_dict: dict[str, int], time_dict: dict[str, tuple[int, int] | None]):
    played_vehicles: list[str] = re.findall(r"^\s{4,}(.*?)\s{4,}.*?$",
                                            re.search(r"^Time Played.*?\n(.*?)\n\n", data, re.M | re.S)[1],
                                            re.M)
    for vehicle in played_vehicles:
        result_dict[vehicle] = 0
        time_dict[vehicle] = None


def process_activity(data: str, result_dict: dict[str, int], time_dict: dict[str, tuple[int, int] | None]):
    activity: list[tuple[str, str]] = re.findall(r"^\s{4,}(.*?)\s{4,}.*?(\d+) SL.*?$",
                                                 re.search(r"^Activity Time.*?\n(.*?)\n\n", data, re.M | re.S)[1],
                                                 re.M)
    for entry in activity:
        if entry[0] not in result_dict:
            result_dict[entry[0]] = int(entry[1])
            time_dict[entry[0]] = None
        result_dict[entry[0]] += int(entry[1])


def process_main_entries(data: str, result_dict: dict[str, int], time_dict: dict[str, tuple[int, int] | None]):
    awards = re.search(r"^Awards.*?$", data, re.M)
    main_entries: list[str] = re.findall(r"^\s*\d?\d:\d\d.*?$",
                                         data if not awards else data[0:awards.start()], re.M)
    for entry in main_entries:
        time_vehicle_match = re.match(r"\s*(.*?)\s{4,}(.*?)\s{4,}", entry)
        vehicle_name = time_vehicle_match[2]
        if vehicle_name not in result_dict:
            result_dict[vehicle_name] = get_reward_value(entry)
            time_dict[vehicle_name] = None
        reward_time = get_time_in_seconds(time_vehicle_match[1])
        if time_dict[vehicle_name] is None:
            time_dict[vehicle_name] = (reward_time, reward_time)
        result_dict[vehicle_name] += get_reward_value(entry)
        time_dict[vehicle_name] = (min(reward_time, time_dict[vehicle_name][0]),
                                   max(reward_time, time_dict[vehicle_name][1]))


def parse_main_rewards(data: str) -> tuple[dict[str, int], dict[str, tuple[int, int] | None]]:
    result_dict: dict[str, int] = {}
    time_dict: dict[str, tuple[int, int] | None] = {}
    process_played_vehicles(data, result_dict, time_dict)
    process_activity(data, result_dict, time_dict)
    process_main_entries(data, result_dict, time_dict)
    return result_dict, time_dict


def get_award_vehicle(award_time: int, time_bounds: dict[str, tuple[int, int] | None]) -> str | None:
    no_data = True
    possible_key = next(iter(time_bounds))
    possible_value = time_bounds[possible_key]
    for key, value in time_bounds.items():
        if value is None:
            continue
        else:
            no_data = False
        if value[0] <= award_time <= value[1]:
            return key
        if possible_value is None or \
                ((award_time < value[0]) and (possible_value[0] > value[0])) or \
                (award_time > value[1]) and ((possible_value[1] < value[1]) or (possible_value[0] > award_time)):
            possible_key = key
            possible_value = value
    if no_data:
        return None
    return possible_key


def process_award_entry(entry: str, result_dict: dict[str, int], time_dict: dict[str, tuple[int, int] | None]) -> int:
    time_award_match = re.match(r"\s*(.*?)\s{4,}(.*?)\s{4,}", entry)
    award_name = time_award_match[2]
    award_value = get_reward_value(entry)
    award_time = get_time_in_seconds(time_award_match[1])
    award_vehicle = get_award_vehicle(award_time, time_dict)
    if award_name in general_awards or award_vehicle is None:
        return award_value
    result_dict[award_vehicle] += award_value
    return 0


def parse_award_rewards(data: str, time_dict: dict[str, tuple[int, int] | None]) -> tuple[dict[str, int], int]:
    result_dict: dict[str, int] = {key: 0 for key in time_dict.keys()}
    general_awards_sum = int((re.search(r"^Other awards\s+(\d+) SL.*?$", data, re.M) or [0, 0])[1])
    awards = re.search(r"^Awards.*?\n(.*?)\n\n", data, re.M | re.S)
    if awards:
        awards_entries: list[str] = re.findall(r"^\s*\d?\d:\d\d.*?$", awards[1], re.M)
        for entry in awards_entries:
            general_awards_sum += process_award_entry(entry, result_dict, time_dict)
    return result_dict, general_awards_sum


def calculate_additional_reward(multiplier: decimal.Decimal, result_dict: dict[str, int], exact_value: int,
                                booster_present: bool) -> str | None:
    estimated_value = 0
    vehicles_quantity = len(result_dict.keys())
    for k, v in result_dict.items():
        temp = decimal.Decimal(v) * multiplier
        if booster_present:
            if vehicles_quantity > 1:
                temp = temp.to_integral(rounding=decimal.ROUND_DOWN)
            else:
                temp = temp.to_integral(rounding=decimal.ROUND_CEILING)
        else:
            temp = temp.to_integral()
        extra_v = int(temp)
        # !!! here might be problem with rounding
        estimated_value += extra_v
        result_dict[k] += extra_v
    return f"Validation of additional reward failed {estimated_value} != {exact_value}" if estimated_value != exact_value else None


def distribute_general_awards(general_awards_sum: int, result_dict: dict[str, int], total: int) -> str | None:
    raw_total = reduce(lambda acc, val: acc + val, result_dict.values(), 0)
    for k, v in result_dict.items():
        extra = round(general_awards_sum * v / raw_total) if raw_total > v else general_awards_sum
        general_awards_sum -= extra
        raw_total -= v
        result_dict[k] += extra
    final_total = reduce(lambda acc, val: acc + val, result_dict.values(), 0)
    return f"Validation of final rewards failed {final_total} != {total}" if final_total != total else None


def process_results(data: str) -> tuple[dict[str, int], str | None]:
    reward_multiplier = decimal.Decimal("0.467") if get_victory_status(data) else decimal.Decimal("0.2")
    vehicles_rewards, time_bounds = parse_main_rewards(data)
    error1 = calculate_additional_reward(reward_multiplier, vehicles_rewards,
                                         int(re.search(r"^Reward for .*\s+(\d+) SL", data, re.M)[1]),
                                         bool(re.search("^Active boosters SL:", data, re.M)))
    vehicles_awards, general_awards_sum = parse_award_rewards(data, time_bounds)
    final_rewards = {key: vehicles_rewards[key] + vehicles_awards[key] for key in vehicles_rewards.keys()}
    error2 = distribute_general_awards(general_awards_sum, final_rewards,
                                       int(re.search(r"^Earned: (\d+) SL", data, re.M)[1]))
    return final_rewards, (None if error2 is None else error2) if error1 is None else \
        "|".join([error1, error2 if error2 is not None else ""])


class Tests(unittest.TestCase):
    def test_correctness(self):
        for path in [p for p in pathlib.Path("./test_data").iterdir() if p.match("*.txt")]:
            with self.subTest(f"Testing file {path}"):
                _, error = process_results(path.read_text())
                self.assertIsNone(error)


def save_new_data_for_testing():
    test_data_path = pathlib.Path("./test_data")
    last_added_file = max([int(re.match(r"(\d+).txt", p.name)[1])
                           for p in test_data_path.iterdir() if p.match("*.txt")])
    new_file = test_data_path / f"{last_added_file + 1}.txt"
    new_file.write_bytes(pathlib.Path("./input.txt").read_bytes())


if __name__ == "__main__":
    # data = pathlib.Path("./input.txt").read_text()
    # res, error = process_results(data)
    # if error is not None:
    #     print(error)
    # print("Result:", res)
    # save_new_data_for_testing()
    # unittest.main()
