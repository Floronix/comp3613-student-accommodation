ACTIONS = (
    "approve_provisionally",
    "verify",
    "reject",
    "activate",
    "deactivate",
    "resubmit",
)


def visible_to_students(listing: dict) -> bool:
    """Only active listings are visible to students."""
    return listing["status"] == "active"
