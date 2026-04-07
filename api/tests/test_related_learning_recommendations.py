from types import SimpleNamespace

from app.services.related_learning_recommendations import (
    RecommendationExplanationInput,
    RecommendationOverlap,
    RelatedLearningItemMatch,
    build_related_learning_candidates_for_pull_request,
    build_recommendation_explanation,
    detect_recurrence_signals,
    is_candidate_eligible,
    rank_matches,
    recommend_related_learning_items,
)


def test_recommendation_overlap_exposes_match_types_and_terms():
    overlap = RecommendationOverlap(
        content_overlap={"persistence"},
        review_overlap={"idempotency"},
        file_path_overlap={"serializers"},
    )

    assert overlap.match_types == ["content_match", "review_match", "file_path_match"]
    assert overlap.review_context_aligned is True
    assert overlap.matched_terms == ["idempotency", "persistence", "serializers"]


def test_is_candidate_eligible_filters_weak_content_only_matches():
    weak_overlap = RecommendationOverlap(
        content_overlap={"tighten", "boundaries", "persistence"},
        review_overlap=set(),
        file_path_overlap=set(),
    )
    strong_overlap = RecommendationOverlap(
        content_overlap={"tighten", "boundaries", "persistence", "service"},
        review_overlap=set(),
        file_path_overlap=set(),
    )

    assert is_candidate_eligible(
        detect_recurrence_signals(weak_overlap),
        same_repository=False,
        category_aligned=False,
    ) is False
    assert is_candidate_eligible(
        detect_recurrence_signals(strong_overlap),
        same_repository=False,
        category_aligned=False,
    ) is True


def test_detect_recurrence_signals_exposes_overlap_summary():
    overlap = RecommendationOverlap(
        content_overlap={"persistence", "service"},
        review_overlap={"idempotency"},
        file_path_overlap=set(),
    )

    signals = detect_recurrence_signals(overlap)

    assert signals.matched_terms == ["idempotency", "persistence", "service"]
    assert signals.match_types == ["content_match", "review_match"]
    assert signals.review_context_aligned is True
    assert signals.content_overlap_size == 2


def test_build_related_learning_candidates_for_pull_request_attaches_repository_and_category_flags():
    current_pr = SimpleNamespace(
        repository=SimpleNamespace(id=10),
        learning_items=[SimpleNamespace(category="design")],
    )
    candidate_item = SimpleNamespace(
        category="design",
        title="title",
        detail="detail",
        evidence="evidence",
        action_for_next_time="action",
        pull_request=SimpleNamespace(
            repository=SimpleNamespace(id=10, full_name="owner/repo"),
            title="older pr",
            body="body",
            author="alice",
            learning_items=[],
            review_comments=[],
        ),
    )

    candidates = build_related_learning_candidates_for_pull_request(current_pr, [candidate_item])

    assert len(candidates) == 1
    assert candidates[0].same_repository is True
    assert candidates[0].category_aligned is True


def test_recommend_related_learning_items_returns_ranked_matches():
    pr = SimpleNamespace(
        repository=SimpleNamespace(id=10, full_name="owner/repo"),
        title="tighten persistence checks",
        body="move validation earlier",
        author="alice",
        learning_items=[SimpleNamespace(category="design", title="t", detail="d", evidence="e", action_for_next_time="a")],
        review_comments=[],
    )
    candidate_item = SimpleNamespace(
        id=1,
        category="design",
        title="validate before persistence",
        detail="move validation before writes",
        evidence="review found missing validation",
        action_for_next_time="keep validation early",
        status="applied",
        confidence=0.9,
        created_at=None,
        pull_request=SimpleNamespace(
            repository=SimpleNamespace(id=10, full_name="owner/repo"),
            title="older fix",
            body="validation cleanup",
            author="alice",
            learning_items=[],
            review_comments=[],
        ),
    )

    matches = recommend_related_learning_items(pr, [candidate_item])

    assert len(matches) == 1
    assert matches[0].same_repository is True
    assert "content_match" in matches[0].match_types


def test_build_recommendation_explanation_separates_reason_generation():
    reasons = build_recommendation_explanation(
        RecommendationExplanationInput(
            matched_terms=["idempotency", "service", "serializer"],
            same_repository=True,
            category_aligned=True,
            review_context_aligned=True,
            status="applied",
            created_at=None,
        )
    )

    assert "Same repository context" in reasons
    assert "Matches the current learning category" in reasons
    assert "Aligned with review comment context" in reasons
    assert "Strong overlap on 3 context terms" in reasons
    assert "Previously marked as applied" in reasons


def test_rank_matches_sorts_by_score_then_confidence():
    lower_confidence = RelatedLearningItemMatch(
        item=SimpleNamespace(status="applied", confidence=0.8, id=1),
        matched_terms=["persistence"],
        match_types=["content_match"],
        same_repository=True,
        score=8,
        recommendation_reasons=["Same repository context"],
    )
    higher_confidence = RelatedLearningItemMatch(
        item=SimpleNamespace(status="applied", confidence=0.95, id=2),
        matched_terms=["persistence"],
        match_types=["content_match"],
        same_repository=True,
        score=8,
        recommendation_reasons=["Same repository context"],
    )

    ranked = rank_matches([lower_confidence, higher_confidence])

    assert [match.item.id for match in ranked] == [2, 1]
