todos = []

def add_todo(task):
  """
  Adds a new task to the todo list with a 'pending' status.
  """
  todos.append({'task': task, 'status': 'pending'})
  print(f"Task '{task}' added.")

def view_todos():
  """
  Displays all tasks in the todo list with their current status.
  """
  if not todos:
    print("No tasks in the todo list.")
    return

  print("\n--- Your Todo List ---")
  for i, todo in enumerate(todos):
    print(f"{i + 1}. {todo['task']} [{todo['status']}]")
  print("----------------------")

def delete_todo(index):
  """
  Deletes a task from the todo list based on its 1-based index.
  """
  if 1 <= index <= len(todos):
    removed_task = todos.pop(index - 1)
    print(f"Task '{removed_task['task']}' deleted.")
  else:
    print("Invalid task number.")

def mark_complete(index):
  """
  Marks a task as complete based on its 1-based index.
  """
  if 1 <= index <= len(todos):
    todos[index - 1]['status'] = 'complete'
    print(f"Task '{todos[index - 1]['task']}' marked as complete.")
  else:
    print("Invalid task number.")