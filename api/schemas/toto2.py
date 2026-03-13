from datetime import date, datetime
from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Draw schemas
# ---------------------------------------------------------------------------

class Toto2DrawBase(BaseModel):
    issue:      int = Field(..., ge=1,            description="Тираж number")
    year:       int = Field(..., ge=1958, le=2100, description="e.g. 2025")
    draw_index: int = Field(1,  ge=1,    le=3,    description="Теглене 1 or 3")
    n1: int = Field(..., ge=1, le=49)
    n2: int = Field(..., ge=1, le=49)
    n3: int = Field(..., ge=1, le=49)
    n4: int = Field(..., ge=1, le=49)
    n5: int = Field(..., ge=1, le=49)
    n6: int = Field(..., ge=1, le=49)
    draw_date: date | None = None

    @model_validator(mode="after")
    def numbers_must_be_unique(self) -> "Toto2DrawBase":
        nums = [self.n1, self.n2, self.n3, self.n4, self.n5, self.n6]
        if len(set(nums)) != 6:
            raise ValueError("All 6 drawn numbers must be unique")
        return self

    @property
    def numbers(self) -> list[int]:
        return sorted([self.n1, self.n2, self.n3, self.n4, self.n5, self.n6])


class Toto2DrawRead(Toto2DrawBase):
    """Returned by the API — includes DB-assigned fields."""
    id:          int
    imported_at: datetime


# ---------------------------------------------------------------------------
# Import schemas  (bulk upload)
# ---------------------------------------------------------------------------

class Toto2ImportRow(BaseModel):
    """
    One parsed row from the converter script.

    Source format (DOCX/TXT):
        Тираж 1/2025, Теглене 1: 3 16 23 36 41 49
        Тираж 1/2014, Теглене 2: 5 12 19 28 33 41   ← pre-2014 two draws
    """
    issue:      int        = Field(..., ge=1)
    year:       int        = Field(..., ge=1958)
    draw_index: int        = Field(1, ge=1, le=3)
    numbers:    list[int]  = Field(..., min_length=6, max_length=6)
    draw_date:  date | None = None

    @model_validator(mode="after")
    def validate_numbers(self) -> "Toto2ImportRow":
        for n in self.numbers:
            if not (1 <= n <= 49):
                raise ValueError(f"Number {n} is out of range 1..49")
        if len(set(self.numbers)) != 6:
            raise ValueError("All 6 numbers must be unique")
        return self


class Toto2ImportPayload(BaseModel):
    """
    Body for POST /toto2/import

    Example:
    {
        "overwrite": false,
        "rows": [
            {"issue": 1, "year": 2025, "draw_index": 1, "numbers": [3,16,23,36,41,49]},
            {"issue": 2, "year": 2025, "draw_index": 1, "numbers": [7,10,33,39,46,49]}
        ]
    }
    """
    rows:       list[Toto2ImportRow]
    overwrite:  bool = Field(
        False,
        description="Overwrite existing draws with same issue/year/draw_index"
    )


class Toto2ImportResult(BaseModel):
    inserted:    int
    skipped:     int
    overwritten: int
    errors:      list[str] = []


# ---------------------------------------------------------------------------
# Stats schemas
# ---------------------------------------------------------------------------

class Toto2NumberStatRead(BaseModel):
    number:          int
    frequency:       int
    last_seen_issue: int | None
    last_seen_year:  int | None
    absence_streak:  int
    updated_at:      datetime


class Toto2StatsResponse(BaseModel):
    total_draws: int
    stats:       list[Toto2NumberStatRead]