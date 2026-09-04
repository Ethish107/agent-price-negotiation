from pydantic import BaseModel, Field


class NegotiationCreate(BaseModel):
    product_id: int

    buyer_target: float = Field(
        gt=0
    )

    buyer_budget: float = Field(
        gt=0
    )

    persona: str

    max_rounds: int = Field(
        default=4,
        ge=1,
        le=10
    )


class RoundResponse(BaseModel):
    id: int

    negotiation_id: int

    round_no: int

    actor: str

    offer_amount: float | None

    action: str

    reasoning: str

    class Config:
        from_attributes = True


class NegotiationResponse(BaseModel):
    id: int

    product_id: int

    buyer_target: float

    buyer_budget: float

    persona: str

    max_rounds: int

    status: str

    agreed_price: float | None

    payment_link_id: str | None

    payment_link_url: str | None

    payment_status: str

    class Config:
        from_attributes = True


class NegotiationDetailResponse(
    NegotiationResponse
):
    rounds: list[RoundResponse] = []