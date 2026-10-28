"""Domain errors and shared problem-response constants."""

PROBLEM = "application/problem+json"


class DomainError(Exception):
    """Base exception for application/domain errors."""

    status = 400
    type = "/errors/domain"
    title = "Request refused"

    def __init__(self, detail: str, **extra):
        super().__init__(detail)
        self.detail = detail
        self.extra = extra


class NoSuchTower(DomainError):
    status = 404
    type = "/errors/no-such-tower"
    title = "No such tower"


class NoSuchDoor(DomainError):
    status = 404
    type = "/errors/no-such-door"
    title = "No such door"


class NoSuchFlat(DomainError):
    status = 400
    type = "/errors/no-such-flat"
    title = "No such flat"


class NoDoorFree(DomainError):
    status = 409
    type = "/errors/no-door-free"
    title = "No free door"

    def __init__(self, detail: str, free_sizes: list[str]):
        super().__init__(detail, free_sizes=free_sizes)


class NoSuchParcel(DomainError):
    status = 404
    type = "/errors/no-such-parcel"
    title = "No such parcel"


class NoSuchCode(DomainError):
    status = 404
    type = "/errors/no-such-code"
    title = "No such pickup code"


class CodeExpired(DomainError):
    status = 404
    type = "/errors/code-expired"
    title = "Pickup code expired"


class CodeUsed(DomainError):
    status = 409
    type = "/errors/code-used"
    title = "This code has already opened its door"


VALIDATION_BODY = (
    422,
    "/errors/validation",
    "The request body is not valid",
)

INTERNAL = (
    500,
    "/errors/internal",
    "Something went wrong",
)

VALIDATION_PARAMS = (
    400,
    "/errors/validation",
    "Invalid query parameter",
)

NOT_FOUND = (
    404,
    "/errors/not-found",
    "No such resource",
)

METHOD_NOT_ALLOWED = (
    405,
    "/errors/method-not-allowed",
    "Method not allowed",
)

HTTP = "/errors/http"
