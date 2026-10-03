from services.ebay.metadata import normalize_condition, snap_condition, parse_condition_policies

SAMPLE = {"itemConditionPolicies": [{
    "categoryId": "261186", "itemConditionRequired": True,
    "itemConditions": [
        {"conditionId": "1000", "conditionDescription": "New"},
        {"conditionId": "2750", "conditionDescription": "Like New"},
        {"conditionId": "5000", "conditionDescription": "Good"},
        {"conditionId": "9999", "conditionDescription": "Mystery"},
    ]}]}


def test_parse_policies():
    r = parse_condition_policies(SAMPLE, "261186")
    assert r["required"] is True
    assert [c["enum"] for c in r["conditions"]] == ["NEW", "LIKE_NEW", "USED_GOOD"]
    assert r["conditions"][1]["label"] == "Like New"


def test_normalize():
    assert normalize_condition("Used - Like New") == "LIKE_NEW"
    assert normalize_condition("USED_GOOD") == "USED_GOOD"
    assert normalize_condition("Used - Fair") == "USED_ACCEPTABLE"
    assert normalize_condition("For Parts") == "FOR_PARTS_OR_NOT_WORKING"
    assert normalize_condition("gibberish") is None
    assert normalize_condition("") is None


def test_snap_prefers_worse_never_upgrades():
    assert snap_condition("USED_GOOD", ["NEW", "USED_GOOD"]) == "USED_GOOD"
    assert snap_condition("USED_EXCELLENT", ["NEW", "USED_GOOD"]) == "USED_GOOD"
    assert snap_condition("USED_ACCEPTABLE", ["NEW", "USED_GOOD"]) == "USED_GOOD"  # nothing worse; nearest better
    assert snap_condition("LIKE_NEW", []) is None
