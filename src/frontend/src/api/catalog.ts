/**
 * Shared fixture data for the frontend api mock seams.
 *
 * Grounding rules:
 * - Course ids/titles/descriptions are REAL seed records from
 *   data/course-desc.jsonl (grounded-UI rule — never invented).
 * - creditHours, meeting strings, prerequisite relationships, and the
 *   completed/in-progress sets are MOCK metadata: in the real system they
 *   live in SQLite (FC33) and verdicts come from the deterministic engine
 *   (CourseRecommendationValidator, FC29–FC32). This file is a labeled
 *   stand-in, swapped out when the FastAPI endpoints are wired.
 * - Prereq fixture entries only cover courses used by the demo narratives;
 *   courses without an entry are treated as having no recorded
 *   prerequisites, which the mock verdicts render as "Prerequisites met".
 */

import type { CourseCatalog, CourseRecord } from './types';

/** id → record — subset of the 75-line seed corpus the UI fixtures need
    (includes the plan-roadmap catalog). */
export const COURSES: CourseCatalog = {
  '1105': { id: '1105', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 2 },
  '1106': { id: '1106', title: 'INTRODUCTION TO COMPUTER SCIENCE AND ENGINEERING.', creditHours: 1 },
  '1301': { id: '1301', title: 'COMPUTER LITERACY', creditHours: 3 },
  '1310': { id: '1310', title: 'INTRODUCTION TO COMPUTERS & PROGRAMMING', creditHours: 3 },
  '1311': { id: '1311', title: 'INTRODUCTION TO PROGRAMMING FOR ENGINEERS', creditHours: 3 },
  '1325': { id: '1325', title: 'OBJECT-ORIENTED PROGRAMMING', creditHours: 3 },
  '2100': { id: '2100', title: 'PRACTICAL COMPUTER HARDWARE/SOFTWARE SYSTEMS.', creditHours: 2 },
  '2312': { id: '2312', title: 'COMPUTER ORGANIZATION & ASSEMBLY LANGUAGE PROGRAMMING', creditHours: 4 },
  '2315': { id: '2315', title: 'DISCRETE STRUCTURES', creditHours: 3 },
  '2440': { id: '2440', title: 'CIRCUIT ANALYSIS', creditHours: 3 },
  '2441': { id: '2441', title: 'DIGITAL LOGIC DESIGN I', creditHours: 3 },
  '3302': { id: '3302', title: 'PROGRAMMING LANGUAGES', creditHours: 3 },
  '3310': {
    id: '3310',
    title: 'FUNDAMENTALS OF SOFTWARE ENGINEERING',
    creditHours: 3,
    description:
      'Software engineering principles, processes, and techniques; software development approaches focusing on functional analysis and functional design methods.',
  },
  '3311': { id: '3311', title: 'OBJECT-ORIENTED SOFTWARE ENGINEERING', creditHours: 3 },
  '3314': { id: '3314', title: 'PROFESSIONAL PRACTICES', creditHours: 1 },
  '3315': {
    id: '3315',
    title: 'THEORETICAL CONCEPTS IN COMPUTER SCIENCE AND ENGINEERING',
    creditHours: 3,
    description:
      'Selected theoretical concepts including regular and context free languages, finite state and pushdown automata, Turing machines, computability, and NP-theory.',
  },
  '3318': {
    id: '3318',
    title: 'ALGORITHMS & DATA STRUCTURES',
    creditHours: 3,
    description:
      'Design and analysis of algorithms with an emphasis on data structures. Approaches to analyzing lower bounds on problems and upper bounds on algorithms.',
  },
  '3320': {
    id: '3320',
    title: 'OPERATING SYSTEMS',
    creditHours: 3,
    description:
      'Functions and components of an operating system, including process synchronization, job scheduling, memory management, file systems protection, and device management.',
  },
  '3330': {
    id: '3330',
    title: 'DATABASE SYSTEMS AND FILE STRUCTURES',
    creditHours: 3,
    description:
      'Database system architecture; file structures for databases, including indexing hashing, and B+-trees; the relational model and algebra; the SQL database language.',
  },
  '3340': {
    id: '3340',
    title: 'INTRODUCTION TO HUMAN COMPUTER INTERACTION',
    creditHours: 3,
    description:
      'Introduction to the interdisciplinary field of Human-Computer Interaction. Studio-based course that bridges cognitive science, ethnography, and anthropological approaches.',
  },
  '3341': {
    id: '3341',
    title: 'DIGITAL LOGIC DESIGN II',
    creditHours: 3,
    description:
      'Hierarchical organization, design, simulation, implementation, and testing of digital systems. Industrial standard computer-aided design tools included.',
  },
  '3380': {
    id: '3380',
    title: 'LINEAR ALGEBRA FOR CSE',
    creditHours: 3,
    description:
      'Solving systems of equations, matrix algebra, determinants, vector spaces, orthogonality and least squares, with applications to computer science.',
  },
  '3442': { id: '3442', title: 'EMBEDDED SYSTEMS I', creditHours: 3 },
  '4308': {
    id: '4308',
    title: 'ARTIFICIAL INTELLIGENCE',
    creditHours: 3,
    description:
      'An introduction to the field of artificial intelligence studying basic techniques such as heuristic search, deduction, learning, problem solving, knowledge representation.',
  },
  '4309': {
    id: '4309',
    title: 'FUNDAMENTALS OF MACHINE LEARNING',
    creditHours: 3,
    description:
      'This course offers an introduction to machine learning. Topics include naive Bayes classifiers, linear regression, linear classifiers, neural networks.',
  },
  '4311': { id: '4311', title: 'NEURAL NETWORKS AND DEEP LEARNING', creditHours: 3 },
  '4316': {
    id: '4316',
    title: 'COMPUTER SYSTEM DESIGN PROJECT I',
    creditHours: 3,
    description:
      'Analysis and design of an industry-type project that involves hardware and software components to meet desired needs within realistic constraints.',
  },
  '4317': {
    id: '4317',
    title: 'COMPUTER SYSTEM DESIGN PROJECT II',
    creditHours: 3,
    description:
      'Implementation, integration, quality assurance through peer review and testing, and deployment of the project designed in CSE 4316; oral presentations.',
  },
  '4321': {
    id: '4321',
    title: 'SOFTWARE TESTING & MAINTENANCE',
    creditHours: 3,
    description:
      'Study of software quality assurance, software testing, and software maintenance processes, methods and techniques including formal review techniques.',
  },
  '4322': { id: '4322', title: 'SOFTWARE PROJECT MANAGEMENT', creditHours: 3 },
  '4333': {
    id: '4333',
    title: 'CLOUD COMPUTING FUNDAMENTALS AND APPLICATIONS',
    creditHours: 3,
    description:
      'Fundamentals of cloud computing: service models, deployment models, distributed resource management, and applications.',
  },
  '4344': {
    id: '4344',
    title: 'COMPUTER NETWORK ORGANIZATION',
    creditHours: 3,
    description:
      'Design and analysis of computer networks. Emphasis on the OSI architecture but discusses other schemes (e.g., ARPAnet). Data link control, local networks.',
  },
  '4351': {
    id: '4351',
    title: 'PARALLEL PROCESSING',
    creditHours: 3,
    description:
      'Theory and practice of parallel processing, including characterization of parallel processors, models for memory, algorithms, and interprocess synchronization.',
  },
  '4360': {
    id: '4360',
    title: 'AUTONOMOUS ROBOT DESIGN AND PROGRAMMING',
    creditHours: 3,
    description:
      'An introduction to robotics and the design and programming of autonomous robot systems. Topics include basic kinematics, dynamics, and control.',
  },
  '4361': { id: '4361', title: 'SOFTWARE DESIGN PATTERNS', creditHours: 3 },
  '4380': {
    id: '4380',
    title: 'INFORMATION SECURITY',
    creditHours: 3,
    description:
      'Hands-on introduction to the basics of security. Includes system security, buffer overflows, a high-level overview of cryptography, firewalls and intrusion detection.',
  },
  '4381': {
    id: '4381',
    title: 'INFORMATION SECURITY II',
    creditHours: 3,
    description:
      'Deeper study of the fundamentals of security, including symmetric key cryptography, public key cryptography, cryptographic protocols, malware design.',
  },
  '4382': {
    id: '4382',
    title: 'SECURE PROGRAMMING',
    creditHours: 3,
    description:
      'This course is an introduction to methods of secure software design and development. Students will learn about the major security problems found in software.',
  },
  '4392': {
    id: '4392',
    title: 'SPECIAL TOPICS',
    creditHours: 3,
    description:
      'New developments in the field of computer science and engineering. Topic may vary from semester to semester. May be repeated for credit when topic changes.',
  },
};

/** Mock prerequisite records (SQLite owns real ones, FC33). */
export const PREREQ_FIXTURE: Record<string, string[]> = {
  '4381': ['4380'],
  '4317': ['4316'],
  '4382': ['3320'],
};

/** Pre-authenticated student baseline (FC36) — mock of the enrollment
    history (completed = passed courses, FC30 context; in-progress = current
    schedule). Real records live in SQLite. */
export const STUDENT_PROGRESS = {
  studentId: 'stu-0001',
  completedCourseIds: ['1105', '1106', '1311', '1325', '2315', '2440', '2441', '2312', '2100'],
  inProgressCourseIds: ['3310', '3320', '3318', '3380'],
};

/** id → meeting string for the seeded demo sections (mock metadata; the
    real schedule lives in SQLite, FC12/FC33). */
export const SECTION_MEETINGS: Record<string, string> = {
  '3310': 'TuTh 9:30–10:50',
  '3320': 'MW 11:30–12:50',
  '3318': 'TuTh 11:00–12:20',
  '3380': 'MW 2:30–3:50',
  '4380': 'TuTh 11:00–12:20',
  '4382': 'MW 2:30–3:50',
  '3330': 'MW 11:30–12:50',
  '3315': 'TuTh 1:00–2:20',
  '4316': 'MW 4:00–5:20',
  '4381': 'MW 10:00–11:20',
  '4308': 'MW 1:00–2:20',
  '4321': 'TuTh 4:00–5:20',
  '4317': 'MW 4:00–5:20',
  '3341': 'F 9:00–11:50',
  '4392': 'TuTh 11:00–12:20',
  '3340': 'F 9:00–11:50',
  '4309': 'MW 5:30–6:50',
  '4344': 'MW 2:30–3:50',
  '4351': 'TuTh 1:00–2:20',
  '4360': 'MW 5:30–6:50',
};

export const CREDIT_CAP = 18;

/** Course lookup with an explicit not-found signal — callers render the id
    alone instead of inventing details (grounded-UI rule). */
export function getCourse(id: string): CourseRecord | null {
  return COURSES[id] ?? null;
}

export function getMeeting(id: string): string | null {
  return SECTION_MEETINGS[id] ?? null;
}