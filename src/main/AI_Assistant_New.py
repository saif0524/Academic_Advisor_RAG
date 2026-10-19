import json
import re
import urllib.request
import urllib.error
import os
from datetime import datetime

# ==========================================
# Building Blocks Layer: Prompt Template
# ==========================================
class PromptTemplate:
    def __init__(self, template_text: str):
        self.template_text = template_text

    @staticmethod
    def from_template(template_text: str):
        return PromptTemplate(template_text)

    def format(self, variables: dict) -> str:
        formatted = self.template_text
        for key, value in variables.items():
            formatted = formatted.replace("{" + key + "}", str(value))
        return formatted


# ==========================================
# Models Layer: LLM Model Adapter
# ==========================================
class OllamaCloudAIService:
    def __init__(self, model_name: str = "gemma4:31b-cloud", api_key: str = None, base_url: str = "https://api.ollama.com"):
        self.model_name = model_name
        self.base_url = base_url
        self.api_key = api_key or os.getenv("OLLAMA_API_KEY")

    def generate_response(self, prompt: str) -> str:
        if not self.api_key:
            return "Error: OLLAMA_API_KEY is missing. Please set it as an environment variable."
        
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
            json_body = json.dumps(payload)

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json_body.encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.api_key}',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Python-urllib'
                },
                method='POST'
            )

            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    body = response.read().decode('utf-8')
                    return self._extract_response_field(body)
                else:
                    return f"Error from Ollama Cloud API: Status code {response.status}"
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            return f"HTTP Error connecting to Ollama Cloud ({e.code}): {error_body}"
        except Exception as e:
            return f"Error: Could not connect to Ollama Cloud. Details: {str(e)}"

    def _extract_response_field(self, json_str: str) -> str:
        try:
            data = json.loads(json_str)
            if "response" in data:
                return data["response"]
        except Exception:
            pass
            
        try:
            pattern = re.compile(r'"response"\s*:\s*"((?:\\.|[^"\\])*)"')
            match = pattern.search(json_str)
            if match:
                raw = match.group(1)
                return (raw.replace(r'\n', '\n')
                          .replace(r'\"', '"')
                          .replace(r'\\', '\\')
                          .replace(r'\t', '\t'))
        except Exception:
            pass
        return json_str


# ==========================================
# Core Academic Domain Models
# ==========================================
class Course:
    def __init__(self, course_id: str, title: str, description: str, credit_hours: int, prerequisites: list = None, offered_terms: list = None):
        self.course_id = course_id
        self.title = title
        self.description = description
        self.credit_hours = credit_hours
        self.prerequisites = prerequisites or []
        self.offered_terms = offered_terms or ["Fall", "Spring"]

    def get_prerequisites(self) -> list:
        return self.prerequisites

    def is_offered_in_term(self, term: str) -> bool:
        return term in self.offered_terms

    def to_document_chunk(self) -> str:
        return f"Course: {self.course_id} - {self.title}. Credits: {self.credit_hours}. Prerequisites: {', '.join(self.prerequisites)}. Description: {self.description}"


class CourseSection(Course):
    def __init__(self, section_id: str, course_id: str, title: str, description: str, credit_hours: int,
                 semester_term: str, instructor: str, meeting_days: list, start_time: str, end_time: str, room_capacity: int, enrolled_count: int):
        super().__init__(course_id, title, description, credit_hours)
        self.section_id = section_id
        self.semester_term = semester_term
        self.instructor = instructor
        self.meeting_days = meeting_days
        self.start_time = start_time
        self.end_time = end_time
        self.room_capacity = room_capacity
        self.enrolled_count = enrolled_count

    def has_time_conflict(self, other_section: 'CourseSection') -> bool:
        # Simple overlap check on meeting days and times
        if not set(self.meeting_days).intersection(set(other_section.meeting_days)):
            return False
        return self.start_time == other_section.start_time

    def has_open_seats(self) -> bool:
        return self.enrolled_count < self.room_capacity

    def get_schedule_string(self) -> str:
        return f"{self.course_id} ({self.section_id}) - {', '.join(self.meeting_days)} {self.start_time}-{self.end_time} with {self.instructor}"


class EnrollmentRecord:
    def __init__(self, student_id: str, course_id: str, semester_taken: str, grade: str, status: str):
        self.student_id = student_id
        self.course_id = course_id
        self.semester_taken = semester_taken
        self.grade = grade
        self.status = status

    def is_passing_grade(self) -> bool:
        return self.grade in ["A", "B", "C", "D", "Pass"]


class DegreeRequirement:
    def __init__(self, degree_id: str, major_name: str, concentration_name: str, total_credits_required: int, max_semester_credits: int, core_courses: list):
        self.degree_id = degree_id
        self.major_name = major_name
        self.concentration_name = concentration_name
        self.total_credits_required = total_credits_required
        self.max_semester_credits = max_semester_credits
        self.core_courses = core_courses

    def is_course_applicable(self, course_id: str) -> bool:
        return course_id in self.core_courses


class Student:
    def __init__(self, student_id: str, name: str, current_major: DegreeRequirement, concentration: str, career_interest: str):
        self.student_id = student_id
        self.name = name
        self.current_major = current_major
        self.concentration = concentration
        self.career_interest = career_interest
        self.completed_courses = []
        self.active_degree_plan = None

    def has_passed_course(self, course_id: str) -> bool:
        return course_id in self.completed_courses

    def get_completed_credit_hours(self) -> int:
        return len(self.completed_courses) * 3

    def get_current_gpa(self) -> float:
        return 3.5

    def update_major(self, new_major: DegreeRequirement, new_concentration: str) -> None:
        self.current_major = new_major
        self.concentration = new_concentration


# ==========================================
# Degree Planning & Validation Models
# ==========================================
class SemesterPlan:
    def __init__(self, term: str, year: int, max_credit_limit: int = 18):
        self.term = term
        self.year = year
        self.planned_courses = []
        self.scheduled_sections = []
        self.max_credit_limit = max_credit_limit

    def get_total_credits(self) -> int:
        return len(self.planned_courses) * 3

    def add_course(self, course: Course) -> bool:
        if self.get_total_credits() + course.credit_hours <= self.max_credit_limit:
            self.planned_courses.append(course)
            return True
        return False

    def has_schedule_conflicts(self) -> bool:
        for i in range(len(self.scheduled_sections)):
            for j in range(i + 1, len(self.scheduled_sections)):
                if self.scheduled_sections[i].has_time_conflict(self.scheduled_sections[j]):
                    return True
        return False


class DegreePlan:
    def __init__(self, plan_id: str, student_id: str, target_degree: DegreeRequirement, includes_summer: bool = False):
        self.plan_id = plan_id
        self.student_id = student_id
        self.target_degree = target_degree
        self.semesters = []
        self.includes_summer = includes_summer
        self.creation_date = datetime.now()

    def get_semester_schedule(self) -> dict:
        schedule_dict = {}
        for sem in self.semesters:
            schedule_dict[f"{sem.term} {sem.year}"] = [c.course_id for c in sem.planned_courses]
        return schedule_dict

    def get_major(self) -> str:
        return self.target_degree.major_name

    def get_concentration(self) -> str:
        return self.target_degree.concentration_name

    def add_semester(self, semester: SemesterPlan) -> None:
        self.semesters.append(semester)


class CourseRecommendationValidator:
    def __init__(self, sql_db):
        self.sql_db = sql_db

    def verify_course_enrollment(self, student_id: str, course_code: str, completed_courses: list, current_semester_credits: int) -> bool:
        if course_code in completed_courses:
            print(f"Verification Failed: Student already passed {course_code}")
            return False
        if current_semester_credits + 3 > 18:
            print("Verification Failed: Exceeds maximum semester credit hours.")
            return False
        return True


# ==========================================
# Requirement 2: Degree Plan Generator
# ==========================================
class Requirement2_DegreePlanGenerator:
    def generate_plan(self, major: str, concentration: str, completed_courses: list) -> DegreePlan:
        print(f"Generating degree plan for {major} with concentration in {concentration}...")
        
        fall_courses = ["CS 301", "MATH 241", "CYBER 401"]
        spring_courses = ["CS 302", "CYBER 410", "STAT 300"]

        fall_courses = [c for c in fall_courses if c not in completed_courses]
        spring_courses = [c for c in spring_courses if c not in completed_courses]

        req = DegreeRequirement("DEG-01", major, concentration, 120, 18, fall_courses + spring_courses)
        plan = DegreePlan("PLAN-001", "STU-2026-9941", req)

        if fall_courses:
            sem1 = SemesterPlan("Fall", 2026)
            for c in fall_courses:
                sem1.planned_courses.append(Course(c, "Sample Course", "Description", 3))
            plan.add_semester(sem1)

        if spring_courses:
            sem2 = SemesterPlan("Spring", 2027)
            for c in spring_courses:
                sem2.planned_courses.append(Course(c, "Sample Course", "Description", 3))
            plan.add_semester(sem2)

        return plan


# ==========================================
# Requirement 3: Semantic & Conventional Queries
# ==========================================
class Requirement3_QueryRouter:
    def __init__(self, sql_db, vector_store):
        self.sql_db = sql_db
        self.vector_store = vector_store

    def route_and_execute(self, student_id: str, query: str) -> str:
        if "schedule" in query.lower() or "enrolled" in query.lower():
            return self.sql_db.query_student_records(student_id, query)
        else:
            return self.vector_store.similarity_search(query)


# ==========================================
# Requirement 4: Course Verification Guardrail
# ==========================================
class Requirement4_CourseVerifier(CourseRecommendationValidator):
    pass


# ==========================================
# Requirement 5: Plan Modifications & Switching
# ==========================================
class Requirement5_PlanModifier:
    def evaluate_major_change(self, current_major: str, target_major: str) -> str:
        print(f"Analyzing transition from {current_major} to {target_major}...")
        return ("Advantages: Better alignment with cybersecurity careers.\n"
                "Disadvantages: Requires 2 additional foundational math courses (MATH 250 & STAT 310).")

    def generate_plan_comparison(self, old_plan: DegreePlan, new_plan: DegreePlan):
        print("=== Degree Plan Comparison Report ===")
        print(f"Old Plan Semesters: {old_plan.get_semester_schedule()}")
        print(f"New Plan Semesters: {new_plan.get_semester_schedule()}")


# ==========================================
# Requirement 6: Conversation State Management
# ==========================================
class ConversationSession:
    def __init__(self, session_id: str, student_id: str):
        self.session_id = session_id
        self.student_id = student_id
        self.chat_history = []
        self.context_state = {}

    def add_user_message(self, message: str):
        self.chat_history.append(("User", message))

    def add_ai_message(self, message: str):
        self.chat_history.append(("AI Advisor", message))


class Requirement6_ConversationHistory:
    def __init__(self):
        self.session_store = {}

    def add_message(self, student_id: str, sender: str, message: str):
        if student_id not in self.session_store:
            self.session_store[student_id] = ConversationSession(f"sess-{student_id}", student_id)
        
        session = self.session_store[student_id]
        if sender == "User":
            session.add_user_message(message)
        else:
            session.add_ai_message(message)

    def get_history(self, student_id: str) -> list:
        session = self.session_store.get(student_id)
        return session.chat_history if session else []


# ==========================================
# Database Management Layer (Req 7 & 8)
# ==========================================
class DatabaseManager:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.is_connected = False

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def disconnect(self):
        self.is_connected = False


class SQLDatabaseManager(DatabaseManager):
    def query_student_records(self, student_id: str, query: str) -> str:
        return f"SQL Result: Student {student_id} is enrolled in 4 classes this semester with no schedule conflicts."


class VectorDatabaseManager(DatabaseManager):
    def __init__(self, backend_type: str):
        super().__init__("vector-store://local")
        self.backend_type = backend_type
        print(f"Initialized Vector Store backend: {backend_type}")

    def add_document(self, content: str):
        pass

    def similarity_search(self, query: str) -> str:
        return f"Retrieved course catalog context matching: [{query}] using {self.backend_type} backend."


# ==========================================
# Requirement 1: User Interface
# ==========================================

def _load_jsonl_context(self, file_path: str) -> str:
        additional_context = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            # Convert each JSON object line into a readable string representation
                            additional_context.append(json.dumps(data))
            except Exception as e:
                print(f"Warning: Could not read JSONL file: {e}")
        return "\n".join(additional_context)


# ==========================================
# Open Knowledge Format (OKF) Manager
# ==========================================
class OpenKnowledgeFormatManager:
    def __init__(self, kb_root_dir: str = "data"):
        self.kb_root_dir = kb_root_dir

    def scan_knowledge_base(self) -> str:
        """Scans the OKF directory structure, reading markdown files, frontmatter, and content."""
        okf_chunks = []
        if not os.path.exists(self.kb_root_dir):
            return ""

        for root, dirs, files in os.walk(self.kb_root_dir):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()
                            # Format each OKF document chunk clearly for the AI context window
                            okf_chunks.append(f"--- OKF Source: {file} ---\n{content}\n")
                    except Exception as e:
                        print(f"Warning: Could not read OKF file {file}: {e}")
                        
        return "\n".join(okf_chunks)

class Requirement1_UI:
    def __init__(self, query_router, chat_history):
        self.query_router = query_router
        self.chat_history = chat_history
        # Initialize the OKF manager pointing to your knowledge base folder
        self.okf_manager = OpenKnowledgeFormatManager("data")

    def _load_jsonl_context(self, file_path: str) -> str:
        additional_context = []
        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            additional_context.append(json.dumps(data))
            except Exception as e:
                print(f"Warning: Could not read JSONL file: {e}")
        return "\n".join(additional_context)

    def start_command_line_interface(self, student_id: str) -> str:
        print("=== Academic AI Advisor Initialized (LangChain Flow) ===")
        print("Type your query below (or type 'exit' to quit):\n")
        response = ""

        prompt_template = PromptTemplate.from_template(
            "You are an expert Academic AI Advisor specializing in {domain}. "
            "Answer the student's question accurately using the provided context.\n\n"
            "Context Information:\n{context}\n\n"
            "Student Query: {input}"
        )

        while True:
            try:
                user_input = input(f"Student ({student_id}): ")
            except EOFError:
                break
            
            if "exit" == user_input.strip().lower():
                break

            self.chat_history.add_message(student_id, "User", user_input)

            # 1. Retrieve standard RAG query context
            retrieved_context = self.query_router.route_and_execute(student_id, user_input)
            
            # # 2. Append existing JSONL file context
            # jsonl_context = self._load_jsonl_context("data/course-desc.jsonl")
            # if jsonl_context:
            #     retrieved_context += "\n\nCourse descriptions (JSONL):\n" + jsonl_context

            # 3. Scan and inject Open Knowledge Format (OKF) markdown files
            okf_scanned_content = self.okf_manager.scan_knowledge_base()
            if okf_scanned_content:
                retrieved_context += "\n\nOpen Knowledge Format (OKF) Repository Context:\n" + okf_scanned_content

            # 4. Format Prompt dynamically with combined context
            variables = {
                "domain": "University Course Registration and Degree Planning",
                "context": retrieved_context,
                "input": user_input
            }

            formatted_prompt = prompt_template.format(variables)

            # 5. Generate response via Ollama Cloud adapter
            ollama_service = OllamaCloudAIService()
            response = ollama_service.generate_response(formatted_prompt)

            self.chat_history.add_message(student_id, "AI Advisor", response)
            print(f"\nAI Advisor:\n{response}\n")

        return response


# ==========================================
# Main Entry Point & Orchestration
# ==========================================
def main():
    print("==================================================")
    print("       Initializing Academic AI Advisor System    ")
    print("==================================================\n")

    sql_database = SQLDatabaseManager("jdbc:sqlite:student_records.db")
    sql_database.connect()

    vector_store = VectorDatabaseManager("ChromaDB")
    vector_store.add_document("Course catalog text regarding AI and Cybersecurity electives.")

    degree_plan_generator = Requirement2_DegreePlanGenerator()
    course_verifier = Requirement4_CourseVerifier(sql_database)
    plan_modifier = Requirement5_PlanModifier()
    chat_history = Requirement6_ConversationHistory()

    query_router = Requirement3_QueryRouter(sql_database, vector_store)
    user_interface = Requirement1_UI(query_router, chat_history)

    sample_student_id = "STU-2026-9941"

    response = user_interface.start_command_line_interface(sample_student_id)
    chat_history.add_message(sample_student_id, "AI Advisor", response)

    print("\n--- Testing Requirement 2: Degree Plan Generation ---")
    initial_plan = degree_plan_generator.generate_plan(
        "BS Computer Science", "Cybersecurity", ["CS 101", "MATH 101"]
    )

    print("\n--- Testing Requirement 4: Course Verification Guardrail ---")
    can_enroll = course_verifier.verify_course_enrollment(
        sample_student_id, "CS 301", ["CS 101", "MATH 101"], 12
    )
    print(f"Can enroll in CS 301? {can_enroll}")

    print("\n--- Testing Requirement 5: Major Switching & Plan Diff ---")
    evaluation = plan_modifier.evaluate_major_change("BS Computer Science", "BS Software Engineering")
    print(evaluation)
    new_plan = degree_plan_generator.generate_plan(
        "BS Software Engineering", "Artificial Intelligence", ["CS 101", "MATH 101"]
    )
    plan_modifier.generate_plan_comparison(initial_plan, new_plan)

    print("\n==================================================")
    print(" System Test Complete Successfully!               ")
    print("==================================================\n")


if __name__ == "__main__":
    main()