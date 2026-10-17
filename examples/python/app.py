from typing_extensions import TypedDict
from helpers import greet

class Person(TypedDict):
    name: str

message = greet("Ada")
person: Person = {"name": "Ada"}
broken: int = "type-error"  # Intentional: diagnostics should mark this assignment.
print(message, person, broken)
