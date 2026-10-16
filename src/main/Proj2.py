import json
import re
import urllib.request
import urllib.error

# Building Blocks Layer: Prompt Template implementation 
# inspired by LangChain's PromptTemplate for dynamic variable formatting.
class PromptTemplate:
    def __init__(self, template_text: str):
        self.template_text = template_text

    @staticmethod
    def from_template(template_text: str):
        return PromptTemplate(template_text)

    def format(self, variables: dict) -> str:
        formatted = self.template_text
        for key, value in variables.items():
            formatted = formatted.replace("{" + key + "}", value)
        return formatted


# Models Layer / LLM Model Adapter: Interfaces with the raw local LLM.
class OllamaAIService:
    def __init__(self, model_name: str, base_url: str):
        self.model_name = model_name
        self.base_url = base_url

    def generate_response(self, prompt: str) -> str:
        try:
            escaped_prompt = (prompt
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r"))

            json_body = f'{{"model": "{self.model_name}", "prompt": "{escaped_prompt}", "stream": false}}'

            req = urllib.request.Request(
                self.base_url + "/api/generate",
                data=json_body.encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )

            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    body = response.read().decode('utf-8')
                    return self._extract_response_field(body)
                else:
                    return f"Error from Ollama API: Status code {response.status}"
        except Exception as e:
            return (f"Error: Could not connect to local Ollama instance. "
                    f"Make sure Ollama is running (`ollama serve`). Details: {str(e)}")

    def _extract_response_field(self, json_str: str) -> str:
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
# Requirement 1: User Interface
# ==========================================
class Requirement1_UI:
    def __init__(self, query_router, chat_history):
        self.query_router = query_router
        self.chat_history = chat_history

    def start_command_line_interface(self, student_id: str) -> str:
        print("=== Academic AI Advisor Initialized (LangChain Flow) ===")
        print("Type your query below (or type 'exit' to quit):\n")
        response = ""

        # 1. Building Blocks Layer: Create a reusable Prompt Template with variables
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

            # 2. Tools & Integrations Layer: Retrieve context (RAG flow)
            retrieved_context = self.query_router.route_and_execute(student_id, user_input)

            # 3. Orchestration / Building Blocks: Format Prompt dynamically
            variables = {
                "domain": "University Course Registration and Degree Planning",
                "context": retrieved_context,
                "input": user_input
            }

            formatted_prompt = prompt_template.format(variables)

            # 4. Models Layer: Generate response via LLM model adapter
            ollama_service = OllamaAIService("phi3", "http://localhost:11434")
            response = ollama_service.generate_response(formatted_prompt)

            self.chat_history.add_message(student_id, "AI Advisor", response)
            print(f"\nAI Advisor:\n{response}\n")

        return response


# ==========================================
# Requirement 2: Multi-Year Degree Plan Generation
# ==========================================
class Requirement2_DegreePlanGenerator:
    class DegreePlan:
        def __init__(self, major: str, concentration: str, semester_schedule: dict):
            self.major = major
            self.concentration = concentration
            self.semester_schedule = semester_schedule

        def get_semester_schedule(self):
            return self.semester_schedule

        def get_major(self):
            return self.major

        def get_concentration(self):
            return self.concentration

    def generate_plan(self, major: str, concentration: str, completed_courses: list):
        print(f"Generating degree plan for {major} with concentration in {concentration}...")
        
        # Define all required courses for this major/concentration
        fall_courses = ["CS 301", "MATH 241", "CYBER 401"]
        spring_courses = ["CS 302", "CYBER 410", "STAT 300"]

        # Filter out courses the student has already completed
        fall_courses = [c for c in fall_courses if c not in completed_courses]
        spring_courses = [c for c in spring_courses if c not in completed_courses]

        mock_plan = {}
        if fall_courses:
            mock_plan["Fall 2026"] = fall_courses
        if spring_courses:
            mock_plan["Spring 2027"] = spring_courses
        
        if not mock_plan:
            mock_plan["Status"] = ["All core courses completed!"]

        return self.DegreePlan(major, concentration, mock_plan)


# ==========================================
# Requirement 3: Semantic and Conventional Queries
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
class Requirement4_CourseVerifier:
    def verify_course_enrollment(self, student_id: str, course_code: str, completed_courses: list,
                                 current_semester_credits: int) -> bool:
        if not self._has_met_prerequisites(course_code, completed_courses):
            print(f"Verification Failed: Prerequisites not met for {course_code}")
            return False
        if course_code in completed_courses:
            print(f"Verification Failed: Student already passed {course_code}")
            return False
        if current_semester_credits + 3 > 18:
            print("Verification Failed: Exceeds maximum semester credit hours.")
            return False
        return True

    def _has_met_prerequisites(self, course_code: str, completed_courses: list) -> bool:
        # TODO : Implement actual prerequisite checking logic based on courseCode
        return True


# ==========================================
# Requirement 5: Plan Modifications & Major Switching
# ==========================================
class Requirement5_PlanModifier:
    def evaluate_major_change(self, current_major: str, target_major: str) -> str:
        # TODO: Make this run on LLM? 
        print(f"Analyzing transition from {current_major} to {target_major}...")
        return ("Advantages: Better alignment with cybersecurity careers.\n"
                "Disadvantages: Requires 2 additional foundational math courses (MATH 250 & STAT 310).")

    def generate_plan_comparison(self, old_plan, new_plan):
        print("=== Degree Plan Comparison Report ===")
        print(f"Old Plan Semesters: {old_plan.get_semester_schedule()}")
        print(f"New Plan Semesters: {new_plan.get_semester_schedule()}")


# ==========================================
# Requirement 6: Conversation State Management
# ==========================================
class Requirement6_ConversationHistory:
    class ChatMessage:
        def __init__(self, sender: str, message: str):
            self.sender = sender
            self.message = message

        def get_sender(self):
            return self.sender

        def get_message(self):
            return self.message

    def __init__(self):
        self.session_store = {}

    def add_message(self, student_id: str, sender: str, message: str):
        if student_id not in self.session_store:
            self.session_store[student_id] = []
        self.session_store[student_id].append(self.ChatMessage(sender, message))

    def get_history(self, student_id: str) -> list:
        return self.session_store.get(student_id, [])


# ==========================================
# Requirement 7: Structural Polyglot Database
# ==========================================
class Requirement7_PolyglotDatabase:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def connect(self):
        print(f"Connected to relational database via: {self.connection_string}")

    def query_student_records(self, student_id: str, query: str) -> str:
        return f"SQL Result: Student {student_id} is enrolled in 4 classes this semester with no schedule conflicts."


# ==========================================
# Requirement 8: Vector Store Manager
# ==========================================
class Requirement8_VectorStoreManager:
    def __init__(self, backend_type: str):
        self.backend_type = backend_type
        print(f"Initialized Vector Store backend: {backend_type}")

    def add_document(self, content: str):
        # Index document embeddings into Chroma or Pinecone or MD file
        pass

    def similarity_search(self, query: str) -> str:
        return f"Retrieved course catalog context matching: [{query}] using {self.backend_type} backend."


# ==========================================
# Main Entry Point & Orchestration
# ==========================================
def main():
    print("==================================================")
    print("       Initializing Academic AI Advisor System    ")
    print("==================================================\n")

    # 1. Initialize Persistence Layers (Requirements 7 & 8)
    sql_database = Requirement7_PolyglotDatabase("jdbc:sqlite:student_records.db")
    sql_database.connect()

    vector_store = Requirement8_VectorStoreManager("ChromaDB")
    vector_store.add_document("Course catalog text regarding AI and Cybersecurity electives.")

    # 2. Initialize Core Logic & Verification Engines (Requirements 2, 4, 5, 6)
    degree_plan_generator = Requirement2_DegreePlanGenerator()
    course_verifier = Requirement4_CourseVerifier()
    plan_modifier = Requirement5_PlanModifier()
    chat_history = Requirement6_ConversationHistory()

    # 3. Initialize Query Router (Requirement 3)
    query_router = Requirement3_QueryRouter(sql_database, vector_store)

    # 4. Initialize User Interface (Requirement 1)
    user_interface = Requirement1_UI(query_router, chat_history)

    # --- Demonstrating Component Outputs ---
    sample_student_id = "STU-2026-9941"

    # Start the command-line interface and capture the response
    response = user_interface.start_command_line_interface(sample_student_id)

    # Store the last response in conversation history
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

    # To start the interactive CLI loop, uncomment the line below:
    # user_interface.start_command_line_interface(sample_student_id)


if __name__ == "__main__":
    main()