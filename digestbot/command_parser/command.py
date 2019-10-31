from __future__ import annotations

from typing import List, Dict, Any

from digestbot.command_parser.argument import Argument
from digestbot.command_parser.exception import TooManyArgumentsError
from digestbot.command_parser.parse_result import Parsed


class Command:
    def __init__(self, name: str, arguments: List[Argument]):
        self.name = name
        self.arguments = arguments

    def parse(self, params: List[str]) -> Dict[str, Any]:
        args = {}
        params_idx = 0
        for arg in self.arguments:
            args[arg.name] = arg.default
            if params_idx >= len(params):
                continue
            p = arg.parse(params[params_idx])
            if isinstance(p, Parsed):
                args[arg.name] = p.value
                params_idx += 1
        if params_idx < len(params):
            raise TooManyArgumentsError(
                f"Too many arguments provided for command `{self.name}`"
            )
        return args


class CommandBuilder:
    def __init__(self, name):
        self.name = name
        self.arguments = []

    def add_argument(self, argument: Argument) -> CommandBuilder:
        self.arguments.append(argument)
        return self

    def build(self) -> Command:
        return Command(self.name, self.arguments)
