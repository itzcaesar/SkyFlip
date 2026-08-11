from app.services.scoring import BazaarScoreInput, classify_score, score_bazaar_opportunity


def test_score_is_bounded_and_explainable() -> None:
    result = score_bazaar_opportunity(
        BazaarScoreInput(
            buy_price=100,
            net_profit=20,
            roi_percent=20,
            liquidity=95,
            transaction_volume=10_000,
            suggested_volume=100,
            confidence=80,
            competition=10,
            volatility=5,
            manipulation_risk=10,
            fill_time_seconds=300,
        )
    )
    assert 0 <= result.score <= 100
    assert result.classification in {"Excellent", "Strong", "Good", "Moderate", "Weak"}
    assert {
        "profitability",
        "roi",
        "liquidity",
        "confidence",
        "risk_penalty",
    } <= result.breakdown.keys()


def test_score_classification_thresholds_are_stable() -> None:
    assert classify_score(90) == "Excellent"
    assert classify_score(80) == "Strong"
    assert classify_score(70) == "Good"
    assert classify_score(60) == "Moderate"
    assert classify_score(59.99) == "Weak"
