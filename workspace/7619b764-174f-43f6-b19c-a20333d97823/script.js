let todos = [];

function displayTodos() {
    const todoList = document.getElementById('todoList');
    todoList.innerHTML = ''; // Clear current list

    todos.forEach((todo, index) => {
        const li = document.createElement('li');
        li.textContent = todo.text;
        if (todo.completed) {
            li.classList.add('completed'); // Add class for styling completed todos
        }

        const completeCheckbox = document.createElement('input');
        completeCheckbox.type = 'checkbox';
        completeCheckbox.checked = todo.completed;
        completeCheckbox.classList.add('complete-checkbox');
        completeCheckbox.dataset.index = index;
        completeCheckbox.addEventListener('change', toggleComplete);

        const deleteBtn = document.createElement('button');
        deleteBtn.textContent = 'Delete';
        deleteBtn.classList.add('delete-btn');
        deleteBtn.dataset.index = index; // Store the index for deletion
        deleteBtn.addEventListener('click', deleteTodo);

        li.prepend(completeCheckbox); // Add checkbox before text
        li.appendChild(deleteBtn);
        todoList.appendChild(li);
    });
}

function addTodo() {
    const todoInput = document.getElementById('todoInput');
    const todoText = todoInput.value.trim();

    if (todoText !== '') {
        todos.push({ text: todoText, completed: false });
        todoInput.value = ''; // Clear input field
        displayTodos(); // Update the display
    }
}

function deleteTodo(event) {
    const indexToDelete = event.target.dataset.index;
    todos.splice(indexToDelete, 1); // Remove the todo from the array
    displayTodos(); // Update the display
}

function toggleComplete(event) {
    const indexToToggle = event.target.dataset.index;
    todos[indexToToggle].completed = !todos[indexToToggle].completed; // Toggle completion status
    displayTodos(); // Update the display
}

document.getElementById('addTodoBtn').addEventListener('click', addTodo);

// Initial display when the page loads
displayTodos();