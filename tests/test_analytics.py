"""
EduNexus AI — Unit Tests for Academic Analytics & Recommendations Engine
"""

import pytest
from services.analytics import (
    calculate_overall_score,
    calculate_topic_scores,
    detect_weak_topics,
    analyze_student_performance,
    analyze_faculty_cohort,
    ALLOWED_TOPICS
)
from services.recommendations import generate_recommendations


def test_calculate_overall_score_empty():
    assert calculate_overall_score([]) == 0.0


def test_calculate_overall_score():
    submissions = [
        {"score": 40},
        {"score": 50},
        {"score": 60}
    ]
    assert calculate_overall_score(submissions) == 50.0


def test_calculate_topic_scores():
    submissions = [
        {"topic": "Arrays", "score": 90, "is_late": False},
        {"topic": "Arrays", "score": 80, "is_late": True},
        {"topic": "Stacks", "score": 40, "is_late": False}
    ]
    scores = calculate_topic_scores(submissions, ALLOWED_TOPICS)
    arrays = next(s for s in scores if s["topic"] == "Arrays")
    stacks = next(s for s in scores if s["topic"] == "Stacks")
    queues = next(s for s in scores if s["topic"] == "Queues")

    assert arrays["score"] == 85.0
    assert arrays["level"] == "Mastered"
    assert arrays["late_count"] == 1
    assert stacks["score"] == 40.0
    assert stacks["level"] == "Needs Focus"
    assert queues["score"] == 0.0
    assert queues["level"] == "Not Attempted"


def test_detect_weak_topics_average_below_50():
    submissions = [
        {"id": 1, "activity_id": 1, "topic": "Recursion", "score": 46, "status": "submitted"}
    ]
    weak = detect_weak_topics(submissions)
    assert len(weak) == 1
    assert weak[0]["topic"] == "Recursion"
    assert weak[0]["score"] == 46.0
    assert weak[0]["is_flagged"] is True
    assert "below 50% threshold" in weak[0]["evidence"]


def test_detect_weak_topics_two_activities_below_50_with_late_evidence():
    submissions = [
        {"id": 1, "activity_id": 1, "activity_title": "Arrays Quiz 1", "topic": "Arrays", "score": 40, "status": "submitted"},
        {"id": 2, "activity_id": 2, "activity_title": "Arrays Assignment", "topic": "Arrays", "score": 45, "status": "late"},
        {"id": 3, "activity_id": 3, "activity_title": "Linked Lists Quiz", "topic": "Linked Lists", "score": 72, "status": "submitted"}
    ]
    weak = detect_weak_topics(submissions)
    assert len(weak) == 1
    arrays_weak = weak[0]
    assert arrays_weak["topic"] == "Arrays"
    assert arrays_weak["score"] == 42.5
    assert arrays_weak["is_flagged"] is True
    # Verify late submission is cited as supporting evidence
    assert "late submission" in arrays_weak["evidence"]


def test_recommendation_contract_fields():
    weak_topics = [
        {
            "topic": "Arrays",
            "score": 42.5,
            "evidence": "Average score 42.5% below 50% threshold; Arrays Assignment: 45% (late submission)",
            "severity": "critical"
        }
    ]
    recs = generate_recommendations(weak_topics)
    assert len(recs) == 1
    r = recs[0]

    # Required contract fields from prompt:
    # Every recommendation must include the topic, score, evidence, recommended action, resource, and priority.
    assert "topic" in r and r["topic"] == "Arrays"
    assert "score" in r and r["score"] == 42.5
    assert "evidence" in r and "late submission" in r["evidence"]
    assert "recommended_action" in r and len(r["recommended_action"]) > 0
    assert "resource" in r and len(r["resource"]) > 0
    assert "priority" in r and r["priority"] in ["High", "Medium", "Low"]


def test_analyze_student_performance():
    student = {"id": 1, "name": "Aanya Patel", "email": "aanya.demo@example.com"}
    submissions = [
        {"id": 1, "activity_id": 1, "activity_title": "Arrays Quiz", "topic": "Arrays", "score": 40, "status": "submitted"},
        {"id": 2, "activity_id": 2, "activity_title": "Arrays Lab", "topic": "Arrays", "score": 45, "status": "late"},
        {"id": 3, "activity_id": 3, "activity_title": "Linked Lists", "topic": "Linked Lists", "score": 72, "status": "submitted"}
    ]
    profile = analyze_student_performance(student, submissions)
    assert profile["student_id"] == 1
    assert profile["student_name"] == "Aanya Patel"
    assert profile["overall_score"] == 52.3
    assert len(profile["weak_topics"]) == 1
    assert profile["weak_topics"][0]["topic"] == "Arrays"


def test_analyze_faculty_cohort():
    students = [
        {"id": 1, "name": "Aanya Patel"},
        {"id": 2, "name": "Rohan Shah"}
    ]
    all_submissions = [
        {"student_id": 1, "topic": "Arrays", "score": 40},
        {"student_id": 1, "topic": "Arrays", "score": 45},
        {"student_id": 2, "topic": "Arrays", "score": 62},
        {"student_id": 2, "topic": "Linked Lists", "score": 48}
    ]
    cohort = analyze_faculty_cohort(students, all_submissions)
    assert cohort["course"] == "Data Structures"
    assert cohort["enrolled_count"] == 2
    assert cohort["class_average"] == round((40 + 45 + 62 + 48) / 4, 1)
    # Both students have at least one weak topic (< 50%)
    assert cohort["at_risk_count"] >= 1
    assert len(cohort["at_risk_students"]) >= 1
    assert all("suggested_intervention" in s for s in cohort["at_risk_students"])


def test_analyze_faculty_cohort_excludes_zero_submission_students_from_at_risk():
    """Newly registered students with 0 submissions must not be fabricated as High Risk."""
    students = [
        {"id": 1, "name": "Graded Student"},
        {"id": 2, "name": "Brand New Student"}
    ]
    all_submissions = [
        {"student_id": 1, "topic": "Arrays", "score": 88}
    ]
    cohort = analyze_faculty_cohort(students, all_submissions)
    assert cohort["enrolled_count"] == 2
    assert cohort["at_risk_count"] == 0
    assert cohort["at_risk_students"] == []


def test_generate_explainable_faculty_insights():
    from services.analytics import generate_explainable_faculty_insights

    # Insufficient data case
    empty_res = generate_explainable_faculty_insights([], [])
    assert empty_res["has_sufficient_data"] is False
    assert empty_res["insights"] == []
    assert "Insufficient assessment data" in empty_res["message"]

    # Real data with low scores
    students = [{"id": 1, "name": "Student 1"}, {"id": 2, "name": "Student 2"}]
    submissions = [
        {"student_id": 1, "activity_id": 10, "activity_title": "DP Quiz 1", "topic": "Dynamic Programming", "score": 42, "status": "submitted"},
        {"student_id": 2, "activity_id": 10, "activity_title": "DP Quiz 1", "topic": "Dynamic Programming", "score": 48, "status": "late"},
        {"student_id": 1, "activity_id": 11, "activity_title": "Arrays Lab", "topic": "Arrays", "score": 90, "status": "submitted"},
    ]
    res = generate_explainable_faculty_insights(students, submissions)
    assert res["has_sufficient_data"] is True
    assert len(res["insights"]) >= 1
    dp_insight = next(i for i in res["insights"] if i["topic"] == "Dynamic Programming")
    assert dp_insight["average_score"] == 45.0
    assert dp_insight["below_threshold_count"] == 2
    assert any("Module average score: 45.0%" in ev for ev in dp_insight["evidence"])
    assert "recommended_action" in dp_insight
    assert "action_type" in dp_insight

