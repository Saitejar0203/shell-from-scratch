"""State owned by one shell process and inherited by pipeline children."""
from dataclasses import dataclass, field

from app.history import History
from app.programmable import ProgrammableCompletions
from app.variables import Variables


@dataclass
class ShellState:
    jobs: dict = field(default_factory=dict)
    history: History = field(default_factory=History)
    variables: Variables = field(default_factory=Variables)
    completions: ProgrammableCompletions = field(default_factory=ProgrammableCompletions)
