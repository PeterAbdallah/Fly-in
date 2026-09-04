# from typing import Any


# def parser(filename: str) -> dict[str, Any]:
#     try:
#         with open(filename, "r") as f:
#             result: dict[str, Any] = {}
#             line_number: int = 1

#             for line in f:
#                 line.strip()
#                 if line[0] == '#' or line[0] == '\n':
#                     continue
#                 else:
#                     keys = [
#                         "nb_drones", "start_hub",
#                         "end_hub", "hub", "connection"
#                     ]
#     except Exception as e:
#         print(e)
