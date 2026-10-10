/**
 * EduNexus AI - Central Mock Data Store
 * Clearly labeled mock datasets for Student, Faculty, and Admin dashboards.
 * Simulates real backend entity responses as documented in docs/api.md.
 */

const EDUNEXUS_MOCK_DATA = {
  isSimulated: true,

  // ==========================================
  // STUDENT DATA
  // ==========================================
  student: {
    profile: {
      id: "std_2026_042",
      name: "Aryan Agrawal",
      role: "Student",
      email: "student.demo@edunexus.edu",
      program: "B.Sc. Information Technology (Honors)",
      semester: "Semester VI (Academic Year 2026)",
      advisor: "Dr. Sarah Mitchell",
      avatarInitials: "AA"
    },
    metrics: {
      overallScore: 82.4,
      Cgpa: 3.72,
      percentile: "Top 12%",
      attendanceRate: 94.5,
      assignmentsSubmitted: 19,
      totalAssignments: 20,
      activeCoursesCount: 4
    },
    enrolledCourses: [
      { id: "CS301", code: "CS-301", title: "Data Structures & Algorithms", instructor: "Dr. Sarah Mitchell", score: 76.5, grade: "B+" },
      { id: "CS304", code: "CS-304", title: "Database Management Systems", instructor: "Prof. Alan Turing", score: 88.0, grade: "A" },
      { id: "CS308", code: "CS-308", title: "Computer Networks & Sockets", instructor: "Dr. Radia Perlman", score: 85.2, grade: "A-" },
      { id: "CS312", code: "CS-312", title: "Software Engineering & Architecture", instructor: "Prof. Grace Hopper", score: 91.0, grade: "A+" }
    ],
    topicMastery: [
      { topic: "Relational Algebra & SQL", score: 94, level: "Mastered", status: "success" },
      { topic: "Object-Oriented Design", score: 91, level: "Mastered", status: "success" },
      { topic: "TCP/IP & Socket Architecture", score: 85, level: "Proficient", status: "info" },
      { topic: "Asymptotic Complexity", score: 74, level: "Moderate", status: "warning" },
      { topic: "Database Normalization (BCNF)", score: 58, level: "Needs Focus", status: "danger" },
      { topic: "Graph Algorithms & Trees", score: 51, level: "Critical Alert", status: "danger" }
    ],
    weakTopicAlerts: [
      {
        id: "alert_01",
        topic: "Graph Algorithms & Trees",
        score: "51%",
        severity: "critical",
        message: "Performance in shortest-path algorithms (Dijkstra, Bellman-Ford) is 26% below class average.",
        recommendedAction: "Complete the 15-minute Graph Traversal review module before Assessment 3."
      },
      {
        id: "alert_02",
        topic: "Database Normalization (BCNF/4NF)",
        score: "58%",
        severity: "warning",
        message: "Lossless join decomposition queries scored under target threshold in Quiz 4.",
        recommendedAction: "Practice the 5 interactive functional dependency decomposition exercises."
      }
    ],
    recommendations: [
      {
        id: "rec_1",
        title: "Spaced Repetition: Dijkstra & Bellman-Ford Flashcards",
        type: "Active Recall",
        duration: "15 mins",
        impact: "+8.5% projected topic improvement",
        badge: "High Priority",
        category: "Algorithms"
      },
      {
        id: "rec_2",
        title: "Interactive Lab: Multi-table Normalization Decomposition",
        type: "Hands-on Practice",
        duration: "25 mins",
        impact: "+6.0% projected topic improvement",
        badge: "Recommended",
        category: "Databases"
      },
      {
        id: "rec_3",
        title: "Recorded Lecture Snippet: Graph Traversal Nuances (L14)",
        type: "Video Review",
        duration: "18 mins",
        impact: "Clarifies DFS vs BFS queue operations",
        badge: "Concept Clarity",
        category: "Algorithms"
      }
    ],
    studyResources: [
      {
        id: "res_1",
        title: "Advanced Graph Algorithms Reference Handbook",
        format: "PDF Document",
        size: "3.2 MB",
        readTime: "20 min read",
        source: "Department Faculty Curated"
      },
      {
        id: "res_2",
        title: "Interactive SQL Normalization Sandbox",
        format: "Interactive Tool",
        size: "Web Sandbox",
        readTime: "Self-paced",
        source: "EduNexus Knowledge Base"
      },
      {
        id: "res_3",
        title: "Network Protocols & OSI 7-Layer Quick Reference",
        format: "Cheat Sheet",
        size: "1.1 MB",
        readTime: "10 min read",
        source: "Core Curriculum Archive"
      }
    ],
    aiAssistantKnowledge: {
      defaultGreetings: "Hello Aryan! I am your EduNexus AI Academic Assistant. I analyze your topic mastery data to provide tailored academic explanations and study strategies. How can I help you today?",
      suggestedPrompts: [
        "Explain Dijkstra's shortest path algorithm step-by-step",
        "How do I determine if a database schema is in BCNF?",
        "What are my weakest topics and how do I improve them?",
        "Give me a quick 3-question quiz on Graph Traversal"
      ],
      responses: {
        "dijkstra": "Dijkstra's Algorithm finds the shortest path from a starting node to all other nodes in a weighted graph with non-negative edge weights.\n\n1. Initialize: Set distance to source node as 0, and all other nodes to infinity (∞). Mark all nodes unvisited.\n2. Select: Choose the unvisited node with the smallest tentative distance.\n3. Relax: For the current node, calculate tentative distances to all unvisited neighbors. If distance(current) + weight < distance(neighbor), update it.\n4. Mark: Mark the current node as visited.\n5. Repeat: Continue until all nodes are visited or destination is reached.\n\nTip for your upcoming quiz: Remember that Dijkstra fails with negative weight edges — use Bellman-Ford instead in that case!",
        "bcnf": "A relational schema R is in Boyce-Codd Normal Form (BCNF) if for every non-trivial functional dependency X → Y, X is a superkey of R.\n\nTo verify BCNF:\n1. Identify all functional dependencies (FDs).\n2. For each FD X → Y, calculate the attribute closure X+.\n3. If X+ does not contain all attributes of the relation, X is NOT a superkey, and BCNF is violated!\n4. Remedy: Decompose R into R1(X ∪ Y) and R2(R - Y + X) to achieve lossless decomposition.\n\nTry applying this to your Assignment 4 exercises on student course enrollments!",
        "weakest": "Based on your latest assessment analytics, your primary focus areas are:\n\n1. Graph Algorithms & Trees (51% Mastery) — Currently 26% below class median.\n2. Database Normalization (58% Mastery) — Struggles noted with BCNF and 4NF decompositions.\n\nRecommendation: Dedicate 30 minutes today to the 'Spaced Repetition Flashcards' under your recommendations panel.",
        "quiz": "Here is a quick diagnostic question:\n\nQuestion: Which data structure is used to optimize the priority queue in Dijkstra's algorithm to achieve O((V + E) log V) time complexity?\n\nA) Simple Array\nB) Min-Heap / Binary Heap\nC) Stack\nD) Doubly Linked List\n\n(Hint: Binary Min-Heap allows extracting minimum distance in O(log V) time!)"
      }
    }
  },

  // ==========================================
  // FACULTY DATA
  // ==========================================
  faculty: {
    profile: {
      id: "fac_2026_018",
      name: "Dr. Sarah Mitchell",
      role: "Faculty",
      title: "Associate Professor & Curriculum Lead",
      department: "Department of Computer Science",
      email: "faculty.demo@edunexus.edu",
      avatarInitials: "SM"
    },
    courses: [
      {
        id: "CS301",
        code: "CS-301",
        title: "Data Structures & Algorithms",
        enrolledCount: 48,
        classAverage: 74.2,
        atRiskCount: 6,
        attendanceRate: 91.2,
        activeAssessments: 3
      },
      {
        id: "CS305",
        code: "CS-305",
        title: "AI Systems Architecture",
        enrolledCount: 42,
        classAverage: 82.6,
        atRiskCount: 2,
        attendanceRate: 95.0,
        activeAssessments: 2
      }
    ],
    topicMasteryDistribution: [
      { topic: "Asymptotic Analysis", avgScore: 84, benchmark: 80, masteryStatus: "Optimal" },
      { topic: "Divide & Conquer Sorting", avgScore: 79, benchmark: 75, masteryStatus: "Optimal" },
      { topic: "Binary Search Trees", avgScore: 73, benchmark: 70, masteryStatus: "Satisfactory" },
      { topic: "Dynamic Programming", avgScore: 61, benchmark: 70, masteryStatus: "Attention Needed" },
      { topic: "Graph Shortest Path & MST", avgScore: 54, benchmark: 70, masteryStatus: "High Concern" }
    ],
    atRiskStudents: [
      {
        id: "std_0102",
        name: "John Miller",
        studentId: "2026-IT-102",
        courseCode: "CS-301",
        currentScore: 48.5,
        riskLevel: "High Risk",
        riskSeverity: "danger",
        indicators: "Missed 3 quizzes; score dropped 22% in Dynamic Programming",
        lastActive: "4 days ago",
        suggestedIntervention: "Schedule 1-on-1 Academic Counseling"
      },
      {
        id: "std_0114",
        name: "Emily Clark",
        studentId: "2026-IT-114",
        courseCode: "CS-301",
        currentScore: 53.0,
        riskLevel: "High Risk",
        riskSeverity: "danger",
        indicators: "Incomplete Graph Traversal Lab; quiz score 44%",
        lastActive: "1 day ago",
        suggestedIntervention: "Assign Targeted Remedial Module"
      },
      {
        id: "std_0129",
        name: "David Lee",
        studentId: "2026-IT-129",
        courseCode: "CS-301",
        currentScore: 57.8,
        riskLevel: "Medium Risk",
        riskSeverity: "warning",
        indicators: "Consecutive decline over last 3 weekly assessments",
        lastActive: "Yesterday",
        suggestedIntervention: "Send Peer Study Group Invitation"
      },
      {
        id: "std_0142",
        name: "Sophia Patel",
        studentId: "2026-IT-142",
        courseCode: "CS-301",
        currentScore: 59.2,
        riskLevel: "Medium Risk",
        riskSeverity: "warning",
        indicators: "Lecture attendance below 70%; lab submissions late",
        lastActive: "Today",
        suggestedIntervention: "Issue Attendance Warning & Office Hour Invite"
      }
    ],
    recentAssessments: [
      { id: "asm_1", title: "Mid-Term Examination: Algorithms", date: "Oct 04, 2026", submissions: "48/48", averageScore: "73.5%", status: "Graded" },
      { id: "asm_2", title: "Quiz 4: Dynamic Programming & Graphs", date: "Oct 08, 2026", submissions: "44/48", averageScore: "62.1%", status: "Needs Review" },
      { id: "asm_3", title: "Lab Project 2: Graph Pathfinding", date: "Due Oct 15, 2026", submissions: "21/48", averageScore: "Pending", status: "Active" }
    ]
  },

  // ==========================================
  // ADMIN DATA
  // ==========================================
  admin: {
    profile: {
      id: "adm_2026_001",
      name: "System Administrator",
      role: "Admin",
      scope: "Institutional Academic Governance",
      email: "admin.demo@edunexus.edu",
      avatarInitials: "SA"
    },
    platformMetrics: {
      totalUsers: 1284,
      totalStudents: 1120,
      totalFaculty: 142,
      totalAdmins: 22,
      activeCourses: 36,
      systemUptime: "99.98%",
      dailyActiveUsers: 846,
      storageUsedGb: "124.6 GB"
    },
    usersDirectory: [
      { id: "usr_01", name: "Aryan Agrawal", email: "student.demo@edunexus.edu", role: "Student", department: "B.Sc. IT (Honors)", status: "Active", joined: "Sep 2024" },
      { id: "usr_02", name: "Dr. Sarah Mitchell", email: "faculty.demo@edunexus.edu", role: "Faculty", department: "Computer Science", status: "Active", joined: "Aug 2023" },
      { id: "usr_03", name: "John Miller", email: "john.miller@edunexus.edu", role: "Student", department: "B.Sc. IT", status: "Active", joined: "Sep 2025" },
      { id: "usr_04", name: "Emily Clark", email: "emily.clark@edunexus.edu", role: "Student", department: "B.Sc. IT", status: "Active", joined: "Sep 2025" },
      { id: "usr_05", name: "Prof. Alan Turing", email: "alan.turing@edunexus.edu", role: "Faculty", department: "Computer Science", status: "Active", joined: "Jan 2022" },
      { id: "usr_06", name: "Dr. Radia Perlman", email: "radia.perlman@edunexus.edu", role: "Faculty", department: "Networking", status: "Active", joined: "Mar 2023" },
      { id: "usr_07", name: "David Lee", email: "david.lee@edunexus.edu", role: "Student", department: "B.Sc. IT", status: "Suspended", joined: "Oct 2024" },
      { id: "usr_08", name: "System Administrator", email: "admin.demo@edunexus.edu", role: "Admin", department: "Institutional IT", status: "Active", joined: "Jan 2020" }
    ],
    systemAuditLogs: [
      { id: "log_1", action: "User Session Authenticated", actor: "student.demo@edunexus.edu", time: "2 mins ago", status: "Success" },
      { id: "log_2", action: "Course Roster Synced", actor: "Automated SIS Sync", time: "15 mins ago", status: "Success" },
      { id: "log_3", action: "Intervention Dispatched", actor: "faculty.demo@edunexus.edu", time: "1 hour ago", status: "Notice" },
      { id: "log_4", action: "Role Permissions Verified", actor: "System Security Daemon", time: "3 hours ago", status: "Success" }
    ]
  }
};

window.EDUNEXUS_MOCK_DATA = EDUNEXUS_MOCK_DATA;
