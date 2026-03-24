from pydantic import BaseModel, field_validator


# --- Shared models ---

class TeamName(BaseModel):
    id: int | str
    name: str


class Season(BaseModel):
    name: str


class Tournament(BaseModel):
    name: str


class RoundInfo(BaseModel):
    round: int | None = None
    name: str | None = None


class EventStatus(BaseModel):
    type: str


class Event(BaseModel):
    id: int | str
    startTimestamp: int
    homeTeam: TeamName
    awayTeam: TeamName
    season: Season
    tournament: Tournament
    roundInfo: RoundInfo | None = None
    status: EventStatus | None = None


# --- Top-level response models ---

class NextPageResponse(BaseModel):
    """Response from /matches/next/{page} or /events/next/{page}"""
    events: list[Event]
    hasNextPage: bool


class NearResponse(BaseModel):
    """Response from /matches/near or /events/near"""
    nextEvent: list[Event] | Event | None = None

    @field_validator("nextEvent", mode="before")
    @classmethod
    def normalise_next_event(cls, v):
        """API sometimes returns a single event dict instead of a list — normalise to list."""
        if isinstance(v, dict):
            return [v]
        return v


class SearchEntity(BaseModel):
    id: int | str
    name: str
    gender: str | None = None
    playerTeamInfo: dict | None = None


class SearchResult(BaseModel):
    entity: SearchEntity


class SearchResponse(BaseModel):
    """Response from /search/{name}"""
    results: list[SearchResult] = []