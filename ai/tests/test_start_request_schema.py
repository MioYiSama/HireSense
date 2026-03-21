from app.models.schemas import StartRequest


def test_start_request_allows_missing_optional_fields():
    request = StartRequest.model_validate(
        {
            "id": "interview-1",
            "job": "backend",
        }
    )

    assert request.resume is None
    assert request.personalization is None
