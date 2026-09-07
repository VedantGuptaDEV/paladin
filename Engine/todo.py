"""
todo.py — CLI Todo App
Usage:
    python todo.py add "Buy groceries"
    python todo.py list
    python todo.py done <id>
    python todo.py delete <id>
    python todo.py clear
"""

import json
import sys
import os
from datetime import datetime

# Ensure UTF-8 output on Windows terminals
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STORE = os.path.join(os.path.dirname(__file__), "todos.json")


# ── Persistence ──────────────────────────────────────────────────────────────

def load() -> list[dict]:
    if not os.path.exists(STORE):
        return []
    with open(STORE, "r", encoding="utf-8") as f:
        return json.load(f)


def save(todos: list[dict]) -> None:
    with open(STORE, "w", encoding="utf-8") as f:
        json.dump(todos, f, indent=2)


def next_id(todos: list[dict]) -> int:
    return max((t["id"] for t in todos), default=0) + 1


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_add(text: str) -> None:
    todos = load()
    todo = {
        "id": next_id(todos),
        "text": text.strip(),
        "done": False,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    todos.append(todo)
    save(todos)
    print(f"  [+] Added [{todo['id']}] {todo['text']}")


def cmd_list() -> None:
    todos = load()
    if not todos:
        print("  No todos yet. Add one with: python todo.py add \"<task>\"")
        return

    print(f"\n  {'ID':<4} {'S':<3} {'Task':<40} {'Created'}")
    print("  " + "─" * 65)
    for t in todos:
        status = "[x]" if t["done"] else "[ ]"
        text = t["text"] if len(t["text"]) <= 38 else t["text"][:35] + "..."
        done_style = "\033[90m" if t["done"] else ""
        reset = "\033[0m" if t["done"] else ""
        print(f"  {done_style}{t['id']:<4} {status:<5} {text:<40} {t['created']}{reset}")
    print()

    total = len(todos)
    done = sum(1 for t in todos if t["done"])
    print(f"  {done}/{total} completed\n")


def cmd_done(todo_id: int) -> None:
    todos = load()
    for t in todos:
        if t["id"] == todo_id:
            if t["done"]:
                print(f"  Already marked done: [{todo_id}] {t['text']}")
            else:
                t["done"] = True
                save(todos)
                print(f"  [x] Marked done: [{todo_id}] {t['text']}")
            return
    print(f"  [!] No todo with id {todo_id}")


def cmd_undone(todo_id: int) -> None:
    todos = load()
    for t in todos:
        if t["id"] == todo_id:
            if not t["done"]:
                print(f"  Already pending: [{todo_id}] {t['text']}")
            else:
                t["done"] = False
                save(todos)
                print(f"  [ ] Marked pending: [{todo_id}] {t['text']}")
            return
    print(f"  [!] No todo with id {todo_id}")


def cmd_delete(todo_id: int) -> None:
    todos = load()
    original = len(todos)
    todos = [t for t in todos if t["id"] != todo_id]
    if len(todos) == original:
        print(f"  [!] No todo with id {todo_id}")
    else:
        save(todos)
        print(f"  [-] Deleted todo [{todo_id}]")


def cmd_edit(todo_id: int, new_text: str) -> None:
    todos = load()
    for t in todos:
        if t["id"] == todo_id:
            old = t["text"]
            t["text"] = new_text.strip()
            save(todos)
            print(f"  [~] Updated [{todo_id}]: \"{old}\" -> \"{t['text']}\"")
            return
    print(f"  [!] No todo with id {todo_id}")


def cmd_clear() -> None:
    confirm = input("  Delete ALL todos? [y/N] ").strip().lower()
    if confirm == "y":
        save([])
        print("  [-] All todos cleared.")
    else:
        print("  Cancelled.")


def usage() -> None:
    print("""
  Todo CLI — commands

    add <task>        Add a new todo
    list              List all todos
    done <id>         Mark a todo as done
    undone <id>       Mark a todo as pending
    delete <id>       Delete a todo
    edit <id> <text>  Edit a todo's text
    clear             Delete all todos
""")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    args = sys.argv[1:]

    if not args:
        usage()
        return

    command = args[0].lower()

    if command == "add":
        if len(args) < 2:
            print("  Usage: python todo.py add \"<task>\"")
        else:
            cmd_add(" ".join(args[1:]))

    elif command == "list":
        cmd_list()

    elif command == "done":
        if len(args) < 2 or not args[1].isdigit():
            print("  Usage: python todo.py done <id>")
        else:
            cmd_done(int(args[1]))

    elif command == "undone":
        if len(args) < 2 or not args[1].isdigit():
            print("  Usage: python todo.py undone <id>")
        else:
            cmd_undone(int(args[1]))

    elif command == "delete":
        if len(args) < 2 or not args[1].isdigit():
            print("  Usage: python todo.py delete <id>")
        else:
            cmd_delete(int(args[1]))

    elif command == "edit":
        if len(args) < 3 or not args[1].isdigit():
            print("  Usage: python todo.py edit <id> <new text>")
        else:
            cmd_edit(int(args[1]), " ".join(args[2:]))

    elif command == "clear":
        cmd_clear()

    else:
        print(f"  Unknown command: {command}")
        usage()


if __name__ == "__main__":
    main()
