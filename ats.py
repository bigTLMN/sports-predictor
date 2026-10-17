"""Against-the-spread grading.

vegas_spread is the home-team line. Negative means the home team is favored.
A home cover is actual_margin + vegas_spread > 0.
"""


def apply_shrink(pred_margin, vegas_spread, weight):
    if weight <= 0 or abs(float(vegas_spread)) <= 1e-6:
        return float(pred_margin)
    market_home_margin = -float(vegas_spread)
    return (1.0 - weight) * float(pred_margin) + weight * market_home_margin


def home_covered(actual_margin, vegas_spread):
    edge = float(actual_margin) + float(vegas_spread)
    if edge > 0:
        return "HOME"
    if edge < 0:
        return "AWAY"
    return "PUSH"


def model_side(pred_margin, vegas_spread):
    """Match aggregate_picks: an exact tie is not a home pick."""
    if float(pred_margin) + float(vegas_spread) > 0:
        return "HOME"
    return "AWAY"


def grade_spread(actual_margin, pred_margin, vegas_spread):
    actual = home_covered(actual_margin, vegas_spread)
    if actual == "PUSH":
        return "PUSH"
    return "WIN" if model_side(pred_margin, vegas_spread) == actual else "LOSS"


def grade_total(actual_total, pred_total, vegas_total):
    edge = float(actual_total) - float(vegas_total)
    if edge == 0:
        return "PUSH"
    picked_over = float(pred_total) > float(vegas_total)
    went_over = edge > 0
    return "WIN" if picked_over == went_over else "LOSS"


def time_split(frame, fraction=0.85):
    """Put every game on the cut date into the test side so one day is not split."""
    ordered = frame.sort_values(["game_date", "gameId"])
    if ordered.empty:
        return ordered, ordered
    cut = min(max(int(len(ordered) * fraction), 1), len(ordered) - 1)
    cut_date = ordered.iloc[cut]["game_date"]
    train = ordered[ordered["game_date"] < cut_date]
    test = ordered[ordered["game_date"] >= cut_date]
    if train.empty:
        train = ordered.iloc[:cut]
        test = ordered.iloc[cut:]
    return train, test


def summarize(results):
    wins = sum(1 for item in results if item == "WIN")
    losses = sum(1 for item in results if item == "LOSS")
    pushes = sum(1 for item in results if item == "PUSH")
    decided = wins + losses
    rate = (wins / decided) if decided else None
    return {"wins": wins, "losses": losses, "pushes": pushes, "rate": rate}
