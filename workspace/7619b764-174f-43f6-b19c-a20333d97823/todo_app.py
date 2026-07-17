todos = []

def add_task(description):
    """Naya task list mein add karta hai."""
    task = {"task": description, "completed": False}
    todos.append(task)
    print(f"Task '{description}' add ho gaya hai.")

def display_tasks():
    """Sabhi tasks ko unki current status ke sath print karta hai."""
    if not todos:
        print("Koi task nahi hai.")
        return

    print("\n--- Your Todo List ---")
    for i, task in enumerate(todos):
        status = "X" if task["completed"] else " "
        print(f"{i + 1}. [{status}] {task['task']}")
    print("----------------------")

def mark_complete(task_index):
    """Ek task ko complete mark karta hai."""
    if 0 <= task_index < len(todos):
        todos[task_index]["completed"] = True
        print(f"Task '{todos[task_index]['task']}' complete mark ho gaya hai.")
    else:
        print("Invalid task number.")

def delete_task(task_index):
    """Ek task ko list se remove karta hai."""
    if 0 <= task_index < len(todos):
        removed_task = todos.pop(task_index)
        print(f"Task '{removed_task['task']}' delete ho gaya hai.")
    else:
        print("Invalid task number.")