from dataclasses import dataclass


def clamp(value: float, lower: float = 0.0, upper: float = 100.0) -> float:
    return max(lower, min(upper, value))


def classify_score(score: float) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Strong"
    if score >= 70:
        return "Good"
    if score >= 60:
        return "Moderate"
    return "Weak"


def classify_risk(score: float) -> str:
    if score >= 80:
        return "EXTREME"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


@dataclass(frozen=True)
class BazaarScoreInput:
    buy_price: float
    net_profit: float
    roi_percent: float
    liquidity: float
    transaction_volume: int
    suggested_volume: int
    confidence: float
    competition: float
    volatility: float | None
    manipulation_risk: float
    fill_time_seconds: int | None


@dataclass(frozen=True)
class ScoreResult:
    score: float
    classification: str
    breakdown: dict[str, float]


def score_bazaar_opportunity(values: BazaarScoreInput) -> ScoreResult:
    """Explainable 0-100 Bazaar score.

    Positive components total 100 before penalties:
    profitability 25, ROI 20, liquidity 15, fill probability 15, confidence 15,
    and stability 10. Competition, volatility, risk, and capital lockup then subtract
    explicit penalties. This function is intentionally the single scoring policy module.
    """

    buy_price = max(values.buy_price, 1.0)
    positive_net = max(values.net_profit, 0.0)
    profitability = clamp(positive_net / (buy_price * 0.10), 0, 1) * 25
    roi = clamp(max(values.roi_percent, 0.0) / 15, 0, 1) * 20
    liquidity = clamp(values.liquidity / 100, 0, 1) * 15
    fill_probability = (
        clamp(values.transaction_volume / max(values.suggested_volume * 10, 1), 0, 1) * 15
    )
    confidence = clamp(values.confidence / 100, 0, 1) * 15
    stability_factor = (
        0.35 if values.volatility is None else 1 - clamp(values.volatility, 0, 100) / 100
    )
    stability = clamp(stability_factor, 0, 1) * 10

    competition_penalty = clamp(values.competition / 100, 0, 1) * 5
    volatility_penalty = (
        0 if values.volatility is None else clamp(values.volatility / 100, 0, 1) * 5
    )
    risk_penalty = clamp(values.manipulation_risk / 100, 0, 1) * 10
    lockup_penalty = (
        0 if values.fill_time_seconds is None else clamp(values.fill_time_seconds / 86400, 0, 1) * 5
    )

    raw_score = (
        profitability
        + roi
        + liquidity
        + fill_probability
        + confidence
        + stability
        - competition_penalty
        - volatility_penalty
        - risk_penalty
        - lockup_penalty
    )
    score = round(clamp(raw_score), 2)
    breakdown = {
        "profitability": round(profitability, 2),
        "roi": round(roi, 2),
        "liquidity": round(liquidity, 2),
        "fill_probability": round(fill_probability, 2),
        "confidence": round(confidence, 2),
        "stability": round(stability, 2),
        "competition_penalty": round(competition_penalty, 2),
        "volatility_penalty": round(volatility_penalty, 2),
        "risk_penalty": round(risk_penalty, 2),
        "capital_lockup_penalty": round(lockup_penalty, 2),
    }
    return ScoreResult(score=score, classification=classify_score(score), breakdown=breakdown)
