import enum


class PolicyStatus(str, enum.Enum):
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    DEPRECATED = "DEPRECATED"
