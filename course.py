# course.py
class Course:
    def __init__(self, course_id, name, instructor, added_by="", fee="Free", notes="", capacity=30):
        self.course_id = course_id
        self.name = name
        self.instructor = instructor
        self.added_by = added_by  # track who added
        self.fee = fee or "Free"
        self.notes = notes or "No additional notes"
        self.capacity = int(capacity) if capacity else 30  # default 30 seats

    class Material:
        def __init__(self, title):
            self.title = title

    def to_string(self):
        return f"{self.course_id},{self.name},{self.instructor},{self.added_by},{self.fee},{self.notes},{self.capacity}"
