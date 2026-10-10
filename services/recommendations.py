"""
EduNexus AI — Evidence-Based Learning Recommendations Engine
Course: Data Structures
Generates deterministic, explainable study recommendations matching the required contract:
[topic, score, evidence, recommended_action, resource, priority]
"""

from typing import Dict, List, Any

# Curated academic action and resource catalog
TOPIC_REMEDIATION_CATALOG = {
    "Arrays": {
        "action": "Review zero-based indexing, sliding window boundaries, and two-pointer traversal techniques.",
        "resource": "Interactive Array Memory & Two-Pointer Sandbox (20 mins)",
        "study_type": "Hands-on Lab"
    },
    "Linked Lists": {
        "action": "Practice pointer realignment invariants, head/tail insertion edge cases, and Fast & Slow pointer cycle detection.",
        "resource": "Visual Linked List Node Pointer Debugger & Trace Tool (20 mins)",
        "study_type": "Interactive Visualizer"
    },
    "Stacks": {
        "action": "Work through LIFO evaluation drills, balanced parentheses validation, and monotonic stack patterns.",
        "resource": "Monotonic Stack Patterns & Infix-to-Postfix Guidebook (25 mins)",
        "study_type": "Reference Guide"
    },
    "Queues": {
        "action": "Review circular buffer wraparound logic and FIFO queue mechanics used in breadth-first search.",
        "resource": "Breadth-First Queue Traversal & Circular Buffer Sandbox (15 mins)",
        "study_type": "Practice Module"
    },
    "Recursion": {
        "action": "Trace recursive call stack frames, identify explicit base cases, and practice tree recursion unwinding.",
        "resource": "Recursion Call-Stack Visualizer & Divide-and-Conquer Drills (30 mins)",
        "study_type": "Visual Debugger"
    }
}


def generate_recommendations(weak_topics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates personalized, evidence-based recommendations for all detected weak topics.
    Every recommendation strictly includes:
    - topic
    - score
    - evidence
    - recommended_action
    - resource
    - priority
    """
    recommendations = []

    for item in weak_topics:
        topic = item.get("topic")
        score = item.get("score", 0.0)
        evidence = item.get("evidence", "Performance below target threshold.")
        severity = item.get("severity", "warning")

        catalog = TOPIC_REMEDIATION_CATALOG.get(topic, {
            "action": f"Review core concepts, lecture slides, and practice 3 foundational problems in {topic}.",
            "resource": f"{topic} Core Reference Handbook & Solved Exercises",
            "study_type": "Review Module"
        })

        priority = "High" if severity == "critical" or score < 45.0 else "Medium"

        recommendations.append({
            "id": f"rec_{topic.lower().replace(' ', '_')}",
            "topic": topic,
            "score": score,
            "evidence": evidence,
            "recommended_action": catalog["action"],
            "resource": catalog["resource"],
            "study_type": catalog.get("study_type", "Practice Module"),
            "priority": priority,
            "projected_impact": "+10-15% expected mastery recovery"
        })

    # If no weak topics are flagged, provide positive maintenance recommendation
    if not recommendations:
        recommendations.append({
            "id": "rec_mastery_enrichment",
            "topic": "Data Structures",
            "score": 85.0,
            "evidence": "Consistent academic performance with all topic averages meeting or exceeding target benchmarks.",
            "recommended_action": "Engage in timed competitive coding challenges to strengthen algorithmic time-complexity efficiency.",
            "resource": "Advanced LeetCode Medium/Hard Patterns Handbook",
            "study_type": "Enrichment",
            "priority": "Low",
            "projected_impact": "Maintains top-tier percentile ranking"
        })

    return recommendations
