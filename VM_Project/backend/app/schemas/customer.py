"""Customer Pydantic v2 schemas."""

from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

if TYPE_CHECKING:
    from app.schemas.policy import PolicyResponse
    from app.schemas.attention import CustomerAttentionItemResponse
    from app.schemas.document import PolicyDocumentResponse
    from app.schemas.claim import ClaimResponse



class CustomerBase(BaseModel):
    customer_code: str = Field(..., description="Unique customer code e.g. CUST-1001")
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    date_of_birth: Optional[date] = None
    tier: str = Field(default="STANDARD", description="STANDARD, VIP, HIGH_NET_WORTH")
    risk_segment: str = Field(default="LOW", description="LOW, MEDIUM, HIGH")
    total_clv: float = Field(default=0.0, description="Customer Lifetime Value in USD")
    assigned_agent: str = "Unassigned"
    city: str
    state: str
    status: str = Field(default="ACTIVE", description="ACTIVE, INACTIVE, DORMANT")


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    tier: Optional[str] = None
    risk_segment: Optional[str] = None
    total_clv: Optional[float] = None
    assigned_agent: Optional[str] = None
    status: Optional[str] = None


class CustomerResponse(CustomerBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerSummary(BaseModel):
    id: str
    customer_code: str
    full_name: str
    email: str
    phone: str
    tier: str
    risk_segment: str
    total_clv: float
    status: str
    active_policies_count: int = 0
    open_attention_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CustomerDetailResponse(CustomerResponse):
    policies: List["PolicyResponse"] = []
    attention_items: List["CustomerAttentionItemResponse"] = []
    documents: List["PolicyDocumentResponse"] = []
    claims: List["ClaimResponse"] = []

    model_config = ConfigDict(from_attributes=True)

