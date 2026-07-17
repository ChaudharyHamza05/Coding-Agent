import uuid

class Task:
    def __init__(self, title, id=None, completed=False):
        self.id = id if id is not None else str(uuid.uuid4())
        self.title = title
        self.completed = completed

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "completed": self.completed
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data['title'], id=data['id'], completed=data['completed'])

    def __repr__(self):
        status = "✓" if self.completed else "✗"
        return f"[{status}] {self.title} (ID: {self.id[:8]}...)"
