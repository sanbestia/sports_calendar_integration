import logging
from functions.search_entity import search_entity, pick_entity
from functions.utils import _ask_yes_no

logger = logging.getLogger(__name__)


def _ask_non_empty(prompt: str) -> str:
    """Prompt the user until they enter a non-empty string."""
    while True:
        value = input(prompt).strip()
        if value:
            return value
        logger.info("This field cannot be empty, please try again.")


def get_ids(tracker=None) -> dict[str, dict[str, str]]:
    """Interactively search for players/teams and return a mapping of entity ID to name, sport, and player_type."""
    id_dict: dict[str, dict[str, str]] = {}

    while True:
        name: str = _ask_non_empty("Enter player/team name: ")
        sport: str = _ask_non_empty("Enter sport to look for: ")

        hits = search_entity(name, sport, tracker=tracker)

        if not hits:
            logger.info("No player/team found with that name, please try again.")
            continue

        chosen = pick_entity(hits)
        if chosen:  # None when user declines; still falls through to the search-again prompt so they can exit without selecting
            id_dict[chosen["id"]] = {  # keyed by entity ID; re-adding the same entity overwrites rather than duplicates
                "name": chosen["name"],
                "sport": chosen["sport"],
                "player_type": chosen["player_type"]
            }

        if not _ask_yes_no("Search for another player/team? Y/N: "):
            return id_dict

        logger.info("")


def main():
    """Standalone entry point for running the ID lookup tool from the command line."""
    from objects.APICallTracker import APICallTracker
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    tracker = APICallTracker()
    results = get_ids(tracker=tracker)

    if not results:
        logger.info("No entries were saved.")
        return

    logger.info("\n--- Results ---")
    for entity_id, data in results.items():
        logger.info(f"{data['name']} | ID: {entity_id} | Type: {data['player_type']} | Sport: {data['sport']}")


if __name__ == '__main__':
    main()