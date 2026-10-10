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


def analyze_student_performance(
    student: Dict[str, Any],
    submissions: List[Dict[str, Any]],
    total_assigned_activities: int = 6
) -> Dict[str, Any]:
    """Generates complete analytics profile for a single student."""
    overall = calculate_overall_score(submissions)
    topic_scores = calculate_topic_scores(submissions)
    weak_topics = detect_weak_topics(submissions)

    total_assigned = max(int(total_assigned_activities or 6), 1)
    completion_rate = round((len(submissions) / total_assigned) * 100, 1) if submissions else 0.0

    return {
        "student_id": student.get("id"),
        "student_name": student.get("name"),
        "email": student.get("email"),
        "course": student.get("course") or "Data Structures",
        "overall_score": overall,
        "completion_rate": min(completion_rate, 100.0),
        "total_submissions": len(submissions),
        "has_assessment_data": len(submissions) > 0,
        "topic_scores": topic_scores,
        "weak_topics": weak_topics
    }


def generate_explainable_faculty_insights(
    students: List[Dict[str, Any]],
    all_submissions: List[Dict[str, Any]],
    activities: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Derives explainable, evidence-backed faculty insights strictly from actual
    assessment and submission records in the database.
    Never fabricates statistics when no submission data exists.
    """
    if not all_submissions:
        return {
            "has_sufficient_data": False,
            "message": "Insufficient assessment data: More student submissions are needed before cohort insights can be generated.",
            "insights": []
        }

    # Group submissions by topic (include ALLOWED_TOPICS plus any custom topics in submissions)
    ordered_topics = list(ALLOWED_TOPICS)
    topic_subs: Dict[str, List[Dict[str, Any]]] = {t: [] for t in ordered_topics}
    for sub in all_submissions:
        t = (sub.get("topic") or "General").strip()
        if t not in topic_subs:
            topic_subs[t] = []
            ordered_topics.append(t)
        topic_subs[t].append(sub)

    insights: List[Dict[str, Any]] = []
    for idx, topic in enumerate(ordered_topics, start=1):
        subs = topic_subs.get(topic, [])
        if not subs:
            continue

        scores = [float(s.get("score", 0)) for s in subs]
        attempt_count = len(scores)
        topic_avg = round(sum(scores) / attempt_count, 1)
        low_subs = [s for s in subs if float(s.get("score", 0)) < 50.0]
        low_count = len(low_subs)
        failure_rate = round((low_count / attempt_count) * 100, 1)

        # Group by activity within this topic to find specific activity-level evidence
        act_groups: Dict[str, List[float]] = {}
        for s in subs:
            act_title = s.get("activity_title") or f"Activity {s.get('activity_id', '')}".strip()
            act_groups.setdefault(act_title, []).append(float(s.get("score", 0)))

        weakest_act_title = ""
        weakest_act_avg = topic_avg
        weakest_act_attempts = attempt_count
        if act_groups:
            weakest_pair = min(
                act_groups.items(),
                key=lambda kv: sum(kv[1]) / len(kv[1])
            )
            weakest_act_title = weakest_pair[0]
            weakest_act_attempts = len(weakest_pair[1])
            weakest_act_avg = round(sum(weakest_pair[1]) / weakest_act_attempts, 1)

        if topic_avg < 50.0 or failure_rate >= 50.0:
            severity = "critical"
            priority = "High"
            recommended_action = (
                f"Assign a remedial micro-quiz on {topic} or review {weakest_act_title or topic} in the next lecture."
            )
            action_type = "assign_remedial_quiz"
            action_label = f"Assign Remedial Quiz ({topic})"
        elif topic_avg < 70.0 or low_count > 0:
            severity = "warning"
            priority = "Medium"
            recommended_action = (
                f"Upload targeted practice material for {topic} and hold an office-hours review session."
            )
            action_type = "add_study_material"
            action_label = f"Add {topic} Study Material"
        else:
            severity = "info"
            priority = "Low"
            recommended_action = (
                f"Cohort mastery in {topic} is strong ({topic_avg}% avg). Introduce advanced problem-solving drills."
            )
            action_type = "publish_announcement"
            action_label = f"Post {topic} Challenge"

        act_evidence = (
            f"{weakest_act_title} has a {weakest_act_avg}% average across {weakest_act_attempts} submission(s)"
            if weakest_act_title else f"{attempt_count} submission(s) recorded"
        )
        if low_count > 0:
            failure_clause = f"{low_count} of {attempt_count} attempt(s) ({failure_rate}%) scored below 50%."
        else:
            failure_clause = f"0 of {attempt_count} attempt(s) scored below 50%."

        evidence_list = [
            f"Module average score: {topic_avg}% across {attempt_count} submission(s)",
            act_evidence,
            failure_clause
        ]

        summary_text = (
            f"Module {idx} ({topic}) has a {topic_avg}% average. "
            f"{act_evidence}; {failure_clause} "
            f"Suggested action: {recommended_action}"
        )

        insights.append({
            "id": f"insight_{topic.lower().replace(' ', '_')}",
            "module_number": idx,
            "topic": topic,
            "average_score": topic_avg,
            "topic_average": topic_avg,
            "attempt_count": attempt_count,
            "below_threshold_count": low_count,
            "low_score_count": low_count,
            "failure_rate": failure_rate,
            "weakest_activity": weakest_act_title,
            "weakest_activity_average": weakest_act_avg,
            "severity": severity,
            "priority": priority,
            "evidence": evidence_list,
            "evidence_text": f"{act_evidence} · {failure_clause}",
            "recommended_action": recommended_action,
            "summary": f"Module {idx}: {topic} ({topic_avg}% Cohort Average)",
            "summary_text": summary_text,
            "action_type": action_type,
            "action_label": action_label,
            "suggested_activity_title": f"Remedial Micro-Quiz: {topic} Fundamentals"
        })

    # Sort insights so critical/lowest-average topics appear first
    insights.sort(key=lambda x: x["topic_average"])

    if not insights:
        return {
            "has_sufficient_data": False,
            "message": "Insufficient assessment data: No topic-linked submissions are available yet.",
            "insights": []
        }

    return {
        "has_sufficient_data": True,
        "message": f"Generated {len(insights)} evidence-based insight(s) from {len(all_submissions)} real submission record(s).",
        "insights": insights
    }


def analyze_faculty_cohort(
    students: List[Dict[str, Any]],
    all_submissions: List[Dict[str, Any]],
    activities: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """Computes course-wide faculty analytics, class averages, at-risk students, and explainable insights."""
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
        if not scores:
            status = "No Data"
        else:
            status = "Optimal" if avg >= 75 else ("Satisfactory" if avg >= 60 else "Attention Needed")
        topic_averages.append({
            "topic": t,
            "avg_score": avg,
            "benchmark": 70.0,
            "mastery_status": status,
            "sample_size": len(scores)
        })

    # Students needing support (only evaluate students who have at least 1 submission record)
    at_risk_students = []
    for s in students:
        subs = student_subs.get(s["id"], [])
        if not subs:
            continue

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
                "student_id": s["id"],
                "name": s["name"],
                "email": s.get("email"),
                "overall_score": student_avg,
                "risk_level": risk_level,
                "risk_severity": "danger" if is_high else "warning",
                "indicators": "; ".join(triggers),
                "primary_concerns": "; ".join(triggers),
                "weak_topics_count": len(weak_topics),
                "primary_weak_topic": primary_weak,
                "suggested_intervention": intervention
            })

    # Sort at-risk students by lowest score first
    at_risk_students.sort(key=lambda x: x["overall_score"])

    explainable_insights = generate_explainable_faculty_insights(students, all_submissions, activities)

    return {
        "course": "Data Structures",
        "enrolled_count": len(students),
        "active_submissions_count": len(all_submissions),
        "class_average": class_average,
        "at_risk_count": len(at_risk_students),
        "topic_mastery_distribution": topic_averages,
        "at_risk_students": at_risk_students,
        "explainable_insights": explainable_insights["insights"],
        "insights_meta": {
            "has_sufficient_data": explainable_insights["has_sufficient_data"],
            "message": explainable_insights["message"]
        }
    }
