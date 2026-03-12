import logging
import os
import requests
import json
from pydantic import ValidationError
from objects.APICallTracker import APICallTracker
from objects.schemas import SearchResponse
from functions.utils import sanitize_for_log

logger = logging.getLogger(__name__)


def search_entity(name: str, sport: str, tracker: APICallTracker) -> list[dict]:
    """Search the AllSports API for a player or team by name and sport.
    Returns a list of result dicts, each containing 'id', 'name', 'type', 'gender', and 'sport'."""
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise ValueError("RAPIDAPI_KEY environment variable is not set")

    url: str = (
        f"https://allsportsapi2.p.rapidapi.com/api/"
        f"{'' if sport.lower() == 'football' else sport.lower() + '/'}"
        f"search/{name.lower()}"
    )

    headers: dict[str, str] = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "allsportsapi2.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        tracker.increment()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.error(f"Couldn't communicate with sports API: {e}")
        return []

    if not response.text:
        return []

    try:
        raw = json.loads(response.text)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON response for search '{sanitize_for_log(name)}': {sanitize_for_log(response.text[:200])}")
        return []

    try:
        parsed = SearchResponse.model_validate(raw)
    except ValidationError as e:
        logger.error(f"Unexpected response structure for search '{sanitize_for_log(name)}': {e}")
        return []

    hits = []
    for result in parsed.results:
        entity = result.entity
        hits.append({
            "id": str(entity.id),
            "name": entity.name,
            "player_type": "player" if entity.playerTeamInfo is not None else "team",
            "gender": entity.gender,
            "sport": sport
        })

    return hits


def _ask_yes_no(prompt: str) -> bool:
    """Prompt the user with a Y/N question, re-asking until a valid answer is given."""
    while True:
        answer = input(prompt).strip().upper()
        if answer in ("Y", "N"):
            return answer == "Y"
        logger.info("Please answer Y or N.")


def pick_entity(hits: list[dict]) -> dict | None:
    """Present a list of search hits to the user and return the chosen one, or None if rejected."""
    if not hits:
        logger.info("No results found.")
        return None

    if len(hits) == 1:
        chosen = hits[0]
    else:
        logger.info("Multiple results found:")
        for i, hit in enumerate(hits):
            gender = f" ({hit['gender']})" if hit['gender'] else ""
            player_type = hit['player_type'].capitalize()
            logger.info(f"  {i + 1}: {hit['name']}{gender} — {player_type}")

        while True:
            try:
                index = int(input(f"Type a number between 1 and {len(hits)}: ")) - 1
                if 0 <= index < len(hits):
                    break
                logger.info(f"Please enter a number between 1 and {len(hits)}.")
            except ValueError:
                logger.info("That's not a valid number, please try again.")

        chosen = hits[index]

    if _ask_yes_no(f"Select '{chosen['name']}' ({chosen['player_type']})? Y/N: "):
        return chosen

    logger.info("Choice discarded.")
    return None