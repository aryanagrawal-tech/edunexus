"""
EduNexus AI — Academic Analytics Engine
Course: Data Structures
Implements deterministic scoring, explainable weak-topic detection, and cohort analysis.
"""

from typing import Dict, List, Any, Optional

ALLOWED_TOPICS = ["Arrays", "Linked Lists", "Stacks", "Queues", "Recursion"]


def calculate_overall_score(submissions: List[Dict[str, Any]]) -> float:
    """Calculates student's cumulative average score across all submissions."""
    if not submissions:
        return 0.0
    total = sum(float(s.get("score", 0)) for s in submissions)
    return round(total / len(submissions), 1)


def calculate_topic_scores(submissions: List[Dict[str, Any]], topics: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Calculates granular diagnostic breakdown across course topics."""
    topic_list = topics or ALLOWED_TOPICS
    topic_map: Dict[str, List[Dict[str, Any]]] = {t: [] for t in topic_list}

    for sub in submissions:
        t = sub.get("topic")
        if t in topic_map:
            topic_map[t].append(sub)

    results = []
    for topic, subs in topic_map.items():
        if subs:
            avg_score = round(sum(float(s["score"]) for s in subs) / len(subs), 1)
            count = len(subs)
            late_count = sum(1 for s in subs if s.get("is_late") or s.get("status") == "late")
            
            if avg_score >= 85:
                level = "Mastered"
                status = "success"
            elif avg_score >= 70:
                level = "Proficient"
                status = "info"
            elif avg_score >= 50:
                level = "Moderate"
                status = "warning"
            else:
                level = "Needs Focus"
                status = "danger"
        else:
            avg_score = 0.0
            count = 0
            late_count = 0
            level = "Not Attempted"
            status = "neutral"

        results.append({
            "topic": topic,
            "score": avg_score,
            "level": level,
            "status": status,
            "submissions_count": count,
            "late_count": late_count
        })

    # Sort descending by score for established topics, weak topics prominent
    return results


def detect_weak_topics(submissions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Explainable weak-topic detection rule:
    Flag a topic when:
    1. Average score for that topic is below 50%, OR
    2. Two or more recent activities for that topic score below 50%.
    Late submission is included as supporting evidence, but does not independently prove weak understanding.
    """
    topic_groups: Dict[str, List[Dict[str, Any]]] = {}
    for sub in submissions:
        t = sub.get("topic")
        if not t:
            continue
        if t not in topic_groups:
            topic_groups[t] = []
        topic_groups[t].append(sub)

    weak_topics = []

    for topic, subs in topic_groups.items():
        if not subs:
            continue

        # Sort chronological (submitted_at or id)
        sorted_subs = sorted(subs, key=lambda x: str(x.get("submitted_at") or x.get("id", "")))
        avg_score = round(sum(float(s["score"]) for s in subs) / len(subs), 1)

        # Count low scores (< 50%)
        low_score_subs = [s for s in sorted_subs if float(s["score"]) < 50.0]
        recent_low_count = len(low_score_subs)

        is_avg_low = avg_score < 50.0
        has_two_recent_low = recent_low_count >= 2

        if is_avg_low or has_two_recent_low:
            # Build explainable evidence text
            evidence_parts = []
            if is_avg_low:
                evidence_parts.append(f"Topic average ({avg_score}%) is below 50% threshold")
            if has_two_recent_low:
                evidence_parts.append(f"{recent_low_count} recent activities scored below 50%")

            activity_details = []
            for s in sorted_subs:
                title = s.get("activity_title") or f"Activity {s.get('activity_id')}"
                score_str = f"{s.get('score')}%"
                if s.get("is_late") or s.get("status") == "late":
                    score_str += " (late submission)"
                activity_details.append(f"{title}: {score_str}")

            evidence_str = "; ".join(evidence_parts) + ". Details: " + ", ".join(activity_details)

            weak_topics.append({
                "topic": topic,
                "score": avg_score,
                "is_flagged": True,
                "severity": "critical" if avg_score < 45.0 or recent_low_count >= 2 else "warning",
                "evidence": evidence_str,
                "low_scores_count": recent_low_count,
                "total_activities": len(subs)
            })

    return weak_topics


def analyze_student_performance(student: Dict[str, Any], submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generates complete analytics profile for a single student."""
    overall = calculate_overall_score(submissions)
    topic_scores = calculate_topic_scores(submissions)
    weak_topics = detect_weak_topics(submissions)

    # Calculate attendance / submission completion heuristic
    total_assigned = 6  # standard 6 course activities
    completion_rate = round((len(submissions) / total_assigned) * 100, 1) if total_assigned else 100.0

    return {
        "student_id": student.get("id"),
        "student_name": student.get("name"),
        "email": student.get("email"),
        "course": "Data Structures",
        "overall_score": overall,
        "completion_rate": min(completion_rate, 100.0),
        "total_submissions": len(submissions),
        "topic_scores": topic_scores,
        "weak_topics": weak_topics
    }


def analyze_faculty_cohort(students: List[Dict[str, Any]], all_submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Computes course-wide faculty analytics, class averages, and at-risk students."""
    # Map submissions by student
    student_subs: Dict[Any, List[Dict[str, Any]]] = {s["id"]: [] for s in students}
    for sub in all_submissions:
        sid = sub.get("student_id")
        if sid in student_subs:
            student_subs[sid].append(sub)

    # Class average
    all_scores = [float(s["score"]) for s in all_submissions]
    class_average = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    # Topic averages across cohort
    topic_map: Dict[str, List[float]] = {t: [] for t in ALLOWED_TOPICS}
    for sub in all_submissions:
        t = sub.get("topic")
        if t in topic_map:
            topic_map[t].append(float(sub["score"]))

    topic_averages = []
    for t in ALLOWED_TOPICS:
        scores = topic_map[t]
        avg = round(sum(scores) / len(scores), 1) if scores else 0.0
        status = "Optimal" if avg >= 75 else ("Satisfactory" if avg >= 60 else "Attention Needed")
        topic_averages.append({
            "topic": t,
            "avg_score": avg,
            "benchmark": 70.0,
            "mastery_status": status,
            "sample_size": len(scores)
        })

    # Students needing support
    at_risk_students = []
    for s in students:
        subs = student_subs.get(s["id"], [])
        student_avg = calculate_overall_score(subs)
        weak_topics = detect_weak_topics(subs)

        # Flag student if overall score < 60% OR has any weak topic flagged
        needs_support = student_avg < 60.0 or len(weak_topics) > 0

        if needs_support:
            # Determine risk level
            is_high = student_avg < 50.0 or len(weak_topics) >= 2 or any(w["severity"] == "critical" for w in weak_topics)
            risk_level = "High Risk" if is_high else "Medium Risk"

            # Formulate triggers
            triggers = []
            if student_avg < 60.0:
                triggers.append(f"Overall average score is {student_avg}%")
            if weak_topics:
                wt_names = [f"{w['topic']} ({w['score']}%)" for w in weak_topics]
                triggers.append(f"Weak mastery in: {', '.join(wt_names)}")

            late_count = sum(1 for sub in subs if sub.get("is_late") or sub.get("status") == "late")
            if late_count > 0:
                triggers.append(f"{late_count} late submission(s) noted")

            # Suggest evidence-based faculty intervention
            primary_weak = weak_topics[0]["topic"] if weak_topics else "Core Fundamentals"
            if is_high:
                intervention = f"Schedule 1-on-1 Academic Counseling on {primary_weak}"
            else:
                intervention = f"Assign Targeted Remedial Practice Module on {primary_weak}"

            at_risk_students.append({
                "id": s["id"],
                "name": s["name"],
                "email": s.get("email"),
                "overall_score": student_avg,
                "risk_level": risk_level,
                "risk_severity": "danger" if is_high else "warning",
                "indicators": "; ".join(triggers),
                "weak_topics_count": len(weak_topics),
                "suggested_intervention": intervention
            })

    # Sort at-risk students by lowest score first
    at_risk_students.sort(key=lambda x: x["overall_score"])

    return {
        "course": "Data Structures",
        "enrolled_count": len(students),
        "class_average": class_average,
        "at_risk_count": len(at_risk_students),
        "topic_mastery_distribution": topic_averages,
        "at_risk_students": at_risk_students
    }
