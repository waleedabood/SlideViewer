# Introduction to Python
### A Beginner-Friendly Overview

Created for developers new to the language

slide#

## Why Python?

- **Simple syntax** — reads like English
- **Massive ecosystem** — 400,000+ packages on PyPI
- **Versatile** — web, data science, AI, automation, scripting
- **Community** — one of the largest developer communities worldwide

> "Life is short, use Python." — Bruce Eckel

slide#

## Variables & Data Types

```python
name = "Alice"          # str
age = 30                # int
height = 5.7            # float
is_active = True        # bool
skills = ["Python", "SQL", "Git"]  # list
```

| Type | Example | Mutable |
|------|---------|---------|
| `str` | `"hello"` | No |
| `int` | `42` | No |
| `list` | `[1, 2, 3]` | Yes |
| `dict` | `{"a": 1}` | Yes |
| `tuple` | `(1, 2)` | No |

slide#

## Control Flow

```python
score = 85

if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
else:
    grade = "C"

for i in range(5):
    print(f"Iteration {i}")

while score > 0:
    score -= 10
```

slide#

## Functions

```python
def greet(name: str, excited: bool = False) -> str:
    """Return a greeting message."""
    msg = f"Hello, {name}!"
    if excited:
        msg = msg.upper()
    return msg

print(greet("World"))
print(greet("Python", excited=True))
```

**Key concepts:**
- Default arguments
- Type hints
- Docstrings
- Return values

slide#

## Lists & Comprehensions

```python
numbers = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

evens = [n for n in numbers if n % 2 == 0]
squares = [n ** 2 for n in numbers]
lookup = {n: n ** 2 for n in numbers}
```

| Expression | Result |
|-----------|--------|
| `evens` | `[2, 4, 6, 8, 10]` |
| `squares` | `[1, 4, 9, 16, 25, ...]` |
| `lookup[5]` | `25` |

slide#

## Error Handling

```python
def safe_divide(a, b):
    try:
        result = a / b
    except ZeroDivisionError:
        return "Cannot divide by zero"
    except TypeError as e:
        return f"Type error: {e}"
    else:
        return result
    finally:
        print("Operation complete")
```

**Best practices:**
1. Catch specific exceptions, not bare `except`
2. Use `finally` for cleanup
3. Raise custom exceptions when appropriate

slide#

## Working with Files

```python
# Writing
with open("output.txt", "w") as f:
    f.write("Hello, file!\n")
    f.write("Second line\n")

# Reading
with open("output.txt", "r") as f:
    for line in f:
        print(line.strip())

# JSON
import json
data = {"name": "Alice", "scores": [95, 87, 92]}
with open("data.json", "w") as f:
    json.dump(data, f, indent=2)
```

> Always use `with` statements for automatic file closing.

slide#

## Popular Libraries

| Domain | Library | Use Case |
|--------|---------|----------|
| Web | **Flask / FastAPI** | REST APIs & web apps |
| Data | **pandas** | DataFrames & analysis |
| ML | **scikit-learn** | Machine learning |
| Deep Learning | **PyTorch** | Neural networks |
| Visualization | **matplotlib** | Charts & plots |
| Automation | **selenium** | Browser automation |
| CLI | **click / typer** | Command-line tools |

slide#

# Next Steps

1. **Practice** — solve problems on LeetCode or HackerRank
2. **Build** — pick a project and ship it
3. **Read** — explore the official docs at [python.org](https://python.org)
4. **Contribute** — find beginner-friendly open source projects

> "The best way to learn is to build something you care about."

### Happy coding!
