from flask import Flask, render_template, request, redirect, url_for, session, flash
from course import Course
import os

app = Flask(__name__)
app.secret_key = "secret123"

DATA_FOLDER = "data"
COURSE_FILE = os.path.join(DATA_FOLDER, "courses.txt")
ENROLL_FILE = os.path.join(DATA_FOLDER, "enrollments.txt")
USER_FILE = os.path.join(DATA_FOLDER, "users.txt")

# Ensure files exist
os.makedirs(DATA_FOLDER, exist_ok=True)
for file in [COURSE_FILE, ENROLL_FILE, USER_FILE]:
    if not os.path.exists(file):
        open(file, "w", encoding="utf-8").close()


# ---------------- File Handling ----------------
def read_courses():
    courses = []
    with open(COURSE_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 4:
                cid = parts[0].strip()
                name = parts[1].strip()
                instructor = parts[2].strip()
                added_by = parts[3].strip()
                fee = parts[4].strip() if len(parts) > 4 else "Free"
                notes = parts[5].strip() if len(parts) > 5 else "No additional notes"
                capacity = parts[6].strip() if len(parts) > 6 else "30"
                courses.append(Course(cid, name, instructor, added_by, fee, notes, capacity))
    return courses


def read_enrollments():
    enrollments = {}
    with open(ENROLL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    student, course_id = line.split(",", 1)
                    enrollments.setdefault(course_id, []).append(student)
                except ValueError:
                    pass
    return enrollments


def read_users():
    users = {}
    with open(USER_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    username, password, role = line.split(",", 2)
                    users[username] = {"password": password, "role": role}
                except ValueError:
                    pass
    return users


def write_user(username, password, role):
    with open(USER_FILE, "a", encoding="utf-8") as f:
        f.write(f"{username},{password},{role}\n")


# ---------------- Routes ----------------
@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("courses"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form.get("username")
    password = request.form.get("password")
    users = read_users()
    if username in users and users[username]["password"] == password:
        session["username"] = username
        session["role"] = users[username]["role"]
        return redirect(url_for("courses"))
    else:
        return render_template("login.html", error="Invalid credentials")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")
        
        # Validation
        if not username or not password or not role:
            return render_template("register.html", error="All fields are required")
        
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")
        
        users = read_users()
        if username in users:
            return render_template("register.html", error="Username already exists")
        
        # Save new user
        write_user(username, password, role)
        return render_template("login.html", success="Registration successful! Please login.")
    
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/courses")
def courses():
    if "username" not in session:
        return redirect(url_for("index"))
    
    course_list = read_courses()
    enrollments = read_enrollments()
    role = session.get("role")
    username = session["username"]
    
    # Search functionality
    search_query = request.args.get("search", "").lower()
    if search_query:
        course_list = [c for c in course_list if 
                      search_query in c.course_id.lower() or 
                      search_query in c.name.lower() or 
                      search_query in c.instructor.lower()]
    
    # Calculate statistics
    total_courses = len(read_courses())
    total_enrollments = sum(len(students) for students in enrollments.values())
    my_enrollments = [cid for cid, students in enrollments.items() if username in students]
    
    stats = {
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "my_courses": len(my_enrollments),
        "available_courses": total_courses - len(my_enrollments) if role == "Student" else total_courses
    }
    
    return render_template("courses.html", courses=course_list, enrollments=enrollments, 
                         role=role, username=username, stats=stats, 
                         my_enrollments=my_enrollments, search_query=search_query)


@app.route("/add_course", methods=["POST"])
def add_course():
    if session.get("role") != "Admin":
        flash("Access Denied: Admin privileges required", "error")
        return redirect(url_for("courses"))
    
    cid = request.form.get("cid")
    name = request.form.get("name")
    instructor = request.form.get("instructor")
    fee = request.form.get("fee", "Free")
    notes = request.form.get("notes", "No additional notes")
    capacity = request.form.get("capacity", "30")
    added_by = session["username"]
    
    if cid and name and instructor:
        # Check if course ID already exists
        existing_courses = read_courses()
        if any(course.course_id == cid for course in existing_courses):
            flash(f"Course ID '{cid}' already exists!", "error")
            return redirect(url_for("courses"))
        
        course = Course(cid, name, instructor, added_by, fee, notes, capacity)
        with open(COURSE_FILE, "a", encoding="utf-8") as f:
            f.write(course.to_string() + "\n")
        flash(f"Course '{name}' added successfully!", "success")
    else:
        flash("Course ID, Name, and Instructor are required", "error")
    
    return redirect(url_for("courses"))


@app.route("/enroll", methods=["POST"])
def enroll():
    if session.get("role") != "Student":
        flash("Only students can enroll in courses", "error")
        return redirect(url_for("courses"))
    
    student = session["username"]
    course_id = request.form.get("course_id")
    
    if student and course_id:
        # Check if already enrolled
        enrollments = read_enrollments()
        if course_id in enrollments and student in enrollments[course_id]:
            flash("You are already enrolled in this course", "info")
            return redirect(url_for("courses"))
        
        # Get course and check capacity
        courses = read_courses()
        course = next((c for c in courses if c.course_id == course_id), None)
        
        if not course:
            flash("Course not found", "error")
            return redirect(url_for("courses"))
        
        # Check if course is full
        current_enrolled = len(enrollments.get(course_id, []))
        if current_enrolled >= course.capacity:
            flash(f"Course '{course.name}' is full! ({course.capacity}/{course.capacity} seats)", "error")
            return redirect(url_for("courses"))
        
        with open(ENROLL_FILE, "a", encoding="utf-8") as f:
            f.write(f"{student},{course_id}\n")
        seats_left = course.capacity - current_enrolled - 1
        flash(f"Successfully enrolled in '{course.name}'! ({seats_left} seats remaining)", "success")
    
    return redirect(url_for("courses"))


@app.route("/delete_enrollment", methods=["POST"])
def delete_enrollment():
    if session.get("role") != "Admin":
        flash("Only admin can delete enrollments", "error")
        return redirect(url_for("courses"))
    
    student = request.form.get("student")
    course_id = request.form.get("course_id")
    
    updated_lines = []
    with open(ENROLL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() != f"{student},{course_id}":
                updated_lines.append(line.strip())
    
    with open(ENROLL_FILE, "w", encoding="utf-8") as f:
        for line in updated_lines:
            if line:
                f.write(line + "\n")
    
    flash(f"Removed {student} from course {course_id}", "success")
    return redirect(url_for("courses"))


@app.route("/delete_course", methods=["POST"])
def delete_course():
    if session.get("role") != "Admin":
        flash("Only admin can delete courses", "error")
        return redirect(url_for("courses"))
    
    course_id = request.form.get("course_id")
    
    # Delete course from courses file
    courses = read_courses()
    updated_courses = [c for c in courses if c.course_id != course_id]
    
    with open(COURSE_FILE, "w", encoding="utf-8") as f:
        for course in updated_courses:
            f.write(course.to_string() + "\n")
    
    # Delete all enrollments for this course
    updated_lines = []
    with open(ENROLL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip().endswith(f",{course_id}"):
                updated_lines.append(line.strip())
    
    with open(ENROLL_FILE, "w", encoding="utf-8") as f:
        for line in updated_lines:
            if line:
                f.write(line + "\n")
    
    flash(f"Course {course_id} and all its enrollments deleted successfully", "success")
    return redirect(url_for("courses"))


@app.route("/unenroll", methods=["POST"])
def unenroll():
    if session.get("role") != "Student":
        flash("Only students can unenroll from courses", "error")
        return redirect(url_for("courses"))
    
    student = session["username"]
    course_id = request.form.get("course_id")
    
    updated_lines = []
    with open(ENROLL_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip() != f"{student},{course_id}":
                updated_lines.append(line.strip())
    
    with open(ENROLL_FILE, "w", encoding="utf-8") as f:
        for line in updated_lines:
            if line:
                f.write(line + "\n")
    
    # Get course name for better message
    courses = read_courses()
    course_name = next((c.name for c in courses if c.course_id == course_id), course_id)
    
    flash(f"Successfully unenrolled from '{course_name}'", "success")
    return redirect(url_for("courses"))


@app.route("/my_courses")
def my_courses():
    if "username" not in session:
        return redirect(url_for("index"))
    
    if session.get("role") != "Student":
        return redirect(url_for("courses"))
    
    username = session["username"]
    enrollments = read_enrollments()
    all_courses = read_courses()
    
    # Get only courses the student is enrolled in
    my_enrolled_courses = []
    for course in all_courses:
        if course.course_id in enrollments and username in enrollments[course.course_id]:
            my_enrolled_courses.append(course)
    
    stats = {
        "total_enrolled": len(my_enrolled_courses),
        "total_available": len(all_courses),
        "can_enroll": len(all_courses) - len(my_enrolled_courses)
    }
    
    return render_template("my_courses.html", courses=my_enrolled_courses, 
                         username=username, stats=stats, enrollments=enrollments)


if __name__ == "__main__":
    app.run(debug=True)
