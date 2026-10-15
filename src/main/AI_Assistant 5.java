import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Scanner;


import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Building Blocks Layer: Prompt Template implementation 
 * inspired by LangChain's PromptTemplate for dynamic variable formatting.
 *[cite: 4, 7, 11, 12]
 */
class PromptTemplate {
    private final String templateText;

    private PromptTemplate(String templateText) {
        this.templateText = templateText;
    }

    public static PromptTemplate fromTemplate(String templateText) {
        return new PromptTemplate(templateText);
    }

    public String format(Map<String, String> variables) {
        String formatted = templateText;
        for (Map.Entry<String, String> entry : variables.entrySet()) {
            formatted = formatted.replace("{" + entry.getKey() + "}", entry.getValue());
        }
        return formatted;
    }
}

/**
 * Models Layer / LLM Model Adapter: Interfaces with the raw local LLM[cite: 4, 7, 9].
 */
class OllamaAIService {
    private final String modelName;
    private final String baseUrl;
    private final HttpClient httpClient;

    public OllamaAIService(String modelName, String baseUrl) {
        this.modelName = modelName;
        this.baseUrl = baseUrl;
        this.httpClient = HttpClient.newHttpClient();
    }

    public String generateResponse(String prompt) {
        try {
            String escapedPrompt = prompt
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r");

            String jsonBody = String.format(
                "{\"model\": \"%s\", \"prompt\": \"%s\", \"stream\": false}",
                modelName, escapedPrompt
            );

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(baseUrl + "/api/generate"))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
                .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() == 200) {
                return extractResponseField(response.body());
            } else {
                return "Error from Ollama API: Status code " + response.statusCode();
            }
        } catch (Exception e) {
            return "Error: Could not connect to local Ollama instance. " +
                   "Make sure Ollama is running (`ollama serve`). Details: " + e.getMessage();
        }
    }

    private String extractResponseField(String json) {
        try {
            Pattern pattern = Pattern.compile("\"response\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"");
            Matcher matcher = pattern.matcher(json);
            if (matcher.find()) {
                String raw = matcher.group(1);
                return raw.replace("\\n", "\n")
                          .replace("\\\"", "\"")
                          .replace("\\\\", "\\")
                          .replace("\\t", "\t");
            }
        } catch (Exception ignored) {}
        return json;
    }
}

// ==========================================
// Requirement 1: User Interface
// ==========================================
class Requirement1_UI {
    private final Requirement3_QueryRouter queryRouter;
    private final Requirement6_ConversationHistory chatHistory;

    public Requirement1_UI(Requirement3_QueryRouter queryRouter, Requirement6_ConversationHistory chatHistory) {
        this.queryRouter = queryRouter;
        this.chatHistory = chatHistory;
    }

    public String startCommandLineInterface(String studentId) {
        Scanner scanner = new Scanner(System.in);
        System.out.println("=== Academic AI Advisor Initialized (LangChain Flow) ===");
        System.out.println("Type your query below (or type 'exit' to quit):\n");
        String response = "";

        // 1. Building Blocks Layer: Create a reusable Prompt Template with variables[cite: 4, 7, 11, 12]
        PromptTemplate promptTemplate = PromptTemplate.fromTemplate(
            "You are an expert Academic AI Advisor specializing in {domain}. " +
            "Answer the student's question accurately using the provided context.\n\n" +
            "Context Information:\n{context}\n\n" +
            "Student Query: {input}"
        );

        while (true) {
            System.out.print("Student (" + studentId + "): ");
            String input = scanner.nextLine();
            if ("exit".equalsIgnoreCase(input.trim())) {
                break;
            }

            chatHistory.addMessage(studentId, "User", input);

            // 2. Tools & Integrations Layer: Retrieve context (RAG flow)[cite: 4, 8]
            String retrievedContext = queryRouter.routeAndExecute(studentId, input);

            // 3. Orchestration / Building Blocks: Format Prompt dynamically[cite: 4, 7, 10, 11, 12]
            Map<String, String> variables = new HashMap<>();
            variables.put("domain", "University Course Registration and Degree Planning");
            variables.put("context", retrievedContext);
            variables.put("input", input);

            String formattedPrompt = promptTemplate.format(variables);

            // 4. Models Layer: Generate response via LLM model adapter[cite: 4, 7, 9, 10]
            OllamaAIService ollamaService = new OllamaAIService("phi3", "http://localhost:11434");
            response = ollamaService.generateResponse(formattedPrompt);

            chatHistory.addMessage(studentId, "AI Advisor", response);
            System.out.println("\nAI Advisor:\n" + response + "\n");
        }
        scanner.close();
        return response;
    }
}



// ==========================================
// Requirement 2: Multi-Year Degree Plan Generation
// ==========================================
class Requirement2_DegreePlanGenerator {
    public static class DegreePlan {
        private String major;
        private String concentration;
        private Map<String, List<String>> semesterSchedule;

        public DegreePlan(String major, String concentration, Map<String, List<String>> semesterSchedule) {
            this.major = major;
            this.concentration = concentration;
            this.semesterSchedule = semesterSchedule;
        }

        public Map<String, List<String>> getSemesterSchedule() {
            return this.semesterSchedule;
        }

        public String getMajor() {
            return this.major;
        }

        public String getConcentration() {
            return this.concentration;
        }
    }

    public DegreePlan generatePlan(String major, String concentration, List<String> completedCourses) {
        System.out.println("Generating degree plan for " + major + " with concentration in " + concentration + "...");
        
        // Define all required courses for this major/concentration
        List<String> fallCourses = new ArrayList<>(List.of("CS 301", "MATH 241", "CYBER 401"));
        List<String> springCourses = new ArrayList<>(List.of("CS 302", "CYBER 410", "STAT 300"));

        // Filter out courses the student has already completed
        fallCourses.removeAll(completedCourses);
        springCourses.removeAll(completedCourses);

        Map<String, List<String>> mockPlan = new HashMap<>();
        if (!fallCourses.isEmpty()) {
            mockPlan.put("Fall 2026", fallCourses);
        }
        if (!springCourses.isEmpty()) {
            mockPlan.put("Spring 2027", springCourses);
        }
        
        if (mockPlan.isEmpty()) {
            mockPlan.put("Status", List.of("All core courses completed!"));
        }

        return new DegreePlan(major, concentration, mockPlan);
    }
}

// ==========================================
// Requirement 3: Semantic and Conventional Queries
// ==========================================
class Requirement3_QueryRouter {
    private final Requirement7_PolyglotDatabase sqlDb;
    private final Requirement8_VectorStoreManager vectorStore;

    public Requirement3_QueryRouter(Requirement7_PolyglotDatabase sqlDb, Requirement8_VectorStoreManager vectorStore) {
        this.sqlDb = sqlDb;
        this.vectorStore = vectorStore;
    }

    public String routeAndExecute(String studentId, String query) {
        if (query.toLowerCase().contains("schedule") || query.toLowerCase().contains("enrolled")) {
            return sqlDb.queryStudentRecords(studentId, query);
        } else {
            return vectorStore.similaritySearch(query);
        }
    }
}

// ==========================================
// Requirement 4: Course Verification Guardrail
// ==========================================
class Requirement4_CourseVerifier {
    public boolean verifyCourseEnrollment(String studentId, String courseCode, List<String> completedCourses,
            int currentSemesterCredits) {
        if (!hasMetPrerequisites(courseCode, completedCourses)) {
            System.out.println("Verification Failed: Prerequisites not met for " + courseCode);
            return false;
        }
        if (completedCourses.contains(courseCode)) {
            System.out.println("Verification Failed: Student already passed " + courseCode);
            return false;
        }
        if (currentSemesterCredits + 3 > 18) {
            System.out.println("Verification Failed: Exceeds maximum semester credit hours.");
            return false;
        }
        return true;
    }

    private boolean hasMetPrerequisites(String courseCode, List<String> completedCourses) {
        //TODO : Implement actual prerequisite checking logic based on courseCode
        return true;
    }
}

// ==========================================
// Requirement 5: Plan Modifications & Major Switching
// ==========================================
class Requirement5_PlanModifier {
    public String evaluateMajorChange(String currentMajor, String targetMajor) {
        //TODO: Make this run on LLM? 
        System.out.println("Analyzing transition from " + currentMajor + " to " + targetMajor + "...");
        return "Advantages: Better alignment with cybersecurity careers.\n" +
                "Disadvantages: Requires 2 additional foundational math courses (MATH 250 & STAT 310).";
    }

    public void generatePlanComparison(Requirement2_DegreePlanGenerator.DegreePlan oldPlan,
            Requirement2_DegreePlanGenerator.DegreePlan newPlan) {
        System.out.println("=== Degree Plan Comparison Report ===");
        System.out.println("Old Plan Semesters: " + oldPlan.getSemesterSchedule());
        System.out.println("New Plan Semesters: " + newPlan.getSemesterSchedule());
    }
}

// ==========================================
// Requirement 6: Conversation State Management
// ==========================================
class Requirement6_ConversationHistory {
    private final Map<String, List<ChatMessage>> sessionStore = new HashMap<>();

    public static class ChatMessage {
        private final String sender;
        private final String message;

        public ChatMessage(String sender, String message) {
            this.sender = sender;
            this.message = message;
        }

        public String getSender() {
            return sender;
        }

        public String getMessage() {
            return message;
        }
    }

    public void addMessage(String studentId, String sender, String message) {
        sessionStore.computeIfAbsent(studentId, k -> new ArrayList<>()).add(new ChatMessage(sender, message));
    }

    public List<ChatMessage> getHistory(String studentId) {
        return sessionStore.getOrDefault(studentId, new ArrayList<>());
    }
}

// ==========================================
// Requirement 7: Structural Polyglot Database
// ==========================================
class Requirement7_PolyglotDatabase {
    private final String connectionString;
    //TODO: Either make real database, or use a separate md file
    public Requirement7_PolyglotDatabase(String connectionString) {
        this.connectionString = connectionString;
    }

    public void connect() {
        System.out.println("Connected to relational database via: " + connectionString);
    }

    public String queryStudentRecords(String studentId, String query) {
        return "SQL Result: Student " + studentId
                + " is enrolled in 4 classes this semester with no schedule conflicts.";
    }
}

// ==========================================
// Requirement 8: Vector Store Manager
// ==========================================
class Requirement8_VectorStoreManager {
    private final String backendType;

    public Requirement8_VectorStoreManager(String backendType) {
        this.backendType = backendType;
        System.out.println("Initialized Vector Store backend: " + backendType);
    }

    public void addDocument(String content) {
        // Index document embeddings into Chroma or Pinecone or MD file
    }

    public String similaritySearch(String query) {
        return "Retrieved course catalog context matching: [" + query + "] using " + backendType + " backend.";
    }
}

// ==========================================
// Main Entry Point & Orchestration
// ==========================================
public class AI_Assistant {
    public static void main(String[] args) {
        System.out.println("==================================================");
        System.out.println("       Initializing Academic AI Advisor System    ");
        System.out.println("==================================================\n");

        // 1. Initialize Persistence Layers (Requirements 7 & 8)
        Requirement7_PolyglotDatabase sqlDatabase = new Requirement7_PolyglotDatabase("jdbc:sqlite:student_records.db");
        sqlDatabase.connect();

        Requirement8_VectorStoreManager vectorStore = new Requirement8_VectorStoreManager("ChromaDB");
        vectorStore.addDocument("Course catalog text regarding AI and Cybersecurity electives.");

        // 2. Initialize Core Logic & Verification Engines (Requirements 2, 4, 5, 6)
        Requirement2_DegreePlanGenerator degreePlanGenerator = new Requirement2_DegreePlanGenerator();
        Requirement4_CourseVerifier courseVerifier = new Requirement4_CourseVerifier();
        Requirement5_PlanModifier planModifier = new Requirement5_PlanModifier();
        Requirement6_ConversationHistory chatHistory = new Requirement6_ConversationHistory();

        // 3. Initialize Query Router (Requirement 3)
        Requirement3_QueryRouter queryRouter = new Requirement3_QueryRouter(sqlDatabase, vectorStore);

        // 4. Initialize User Interface (Requirement 1)
        Requirement1_UI userInterface = new Requirement1_UI(queryRouter, chatHistory);

        // --- Demonstrating Component Outputs ---
        String sampleStudentId = "STU-2026-9941";

        // Start the command-line interface and capture the response
        String response = userInterface.startCommandLineInterface(sampleStudentId);

        // Store the last response in conversation history
        chatHistory.addMessage(sampleStudentId, "AI Advisor", response);

        System.out.println("\n--- Testing Requirement 2: Degree Plan Generation ---");
        Requirement2_DegreePlanGenerator.DegreePlan initialPlan = degreePlanGenerator.generatePlan(
                "BS Computer Science", "Cybersecurity", List.of("CS 101", "MATH 101"));

        System.out.println("\n--- Testing Requirement 4: Course Verification Guardrail ---");
        boolean canEnroll = courseVerifier.verifyCourseEnrollment(
                sampleStudentId, "CS 301", List.of("CS 101", "MATH 101"), 12);
        System.out.println("Can enroll in CS 301? " + canEnroll);

        System.out.println("\n--- Testing Requirement 5: Major Switching & Plan Diff ---");
        String evaluation = planModifier.evaluateMajorChange("BS Computer Science", "BS Software Engineering");
        System.out.println(evaluation);
        Requirement2_DegreePlanGenerator.DegreePlan newPlan = degreePlanGenerator.generatePlan(
                "BS Software Engineering", "Artificial Intelligence", List.of("CS 101", "MATH 101", "CS 301"));
        planModifier.generatePlanComparison(initialPlan, newPlan);

        System.out.println("\n==================================================");
        System.out.println(" System Test Complete Successfully!               ");
        System.out.println("==================================================\n");

        // To start the interactive CLI loop, uncomment the line below:
        // userInterface.startCommandLineInterface(sampleStudentId);
    }
}