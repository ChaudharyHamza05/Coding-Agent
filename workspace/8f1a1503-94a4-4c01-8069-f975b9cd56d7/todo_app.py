
todo_list = []

def add_task(description):
    task = {"task": description, "completed": False}
    todo_list.append(task)
    print(f"Task '{description}' added.")

def display_tasks():
    if not todo_list:
        print("No tasks in the list.")
        return
    print("\n--- To-Do List ---")
    for i, task in enumerate(todo_list):
        status = "✓" if task["completed"] else " "
        print(f"{i + 1}. [{status}] {task["task"]}")
    print("------------------")
