"""
Script to convert Trello JSON data to user story template format.

Story attributes:
- Story title
- Story ID
- Priority
- Story points
- Story body
- Acceptance criteria
- Notes

Trello card format:
"(<story-points>) <title>: <story body>"
e.g. "(2) Basic Entry Form: As a potential customer, I want to..."

Trello description format:
"
# Acceptance Criteria
- <criterion-1> 
- <criterion-2>
...
- <criterion-n> 

# Notes
- <note-1>
- <note-2>
...
- <note-n> 
"

- Specify priority with lists
- Add role as a tag (not a part of template)

JSON fields:
- desc - Description (acceptance criteria and notes)
- name - Story content (points, title and body)
"""

import slides

from dataclasses import dataclass
import sys
import json
from typing import List, Dict, Tuple
import re


PRIORITIES = {
    "must have": "M",
    "should have": "S",
    "could have": "C",
}


CARD_PATTERN = r"\(([0-9^\s]+)\)([\S\s^:]+):([\S\s]+)"
CRITERIA_PATTERN = r"# Acceptance Criteria\n\n(- [\S\s^\n]+[\n])+"
NOTES_PATTERN = r"# Notes\n(- [\w\s^\n]+[\n]*)+"

CARD_REGEX = re.compile(CARD_PATTERN)
CRITERIA_REGEX = re.compile(CRITERIA_PATTERN)
NOTES_REGEX = re.compile(NOTES_PATTERN)


@dataclass
class UserStory:
    id_: str
    title: str
    body: str
    priority: str
    points: str
    criteria: List[str]
    notes: List[str]


def validate_card(card: dict) -> bool:
    """ Returns True if the given Trello card JSON object conforms to the required story format, otherwise returns False.  
    
    Arguments: 
        card {dict} -- Trello card JSON to be validated

    Returns:
        bool - True if given card is valid, otherwise False
    """
    return CARD_REGEX.match(card["name"]) is not None


def parse_bullets(target: str) -> Tuple[str, List[str]]:
    """Returns the list of bullet points from a string of the the format "<heading>\n- <bullet-1>\n- <bullet-2>..."  
    
    Arguments:
        target {str} -- String to be parsed
    
    Returns:
        List[str] -- List of extracted bullet points (without leading hyphen)
    """
    target = re.sub(r"(-|=){3,}\n", "", target)
    elements = target.split("\n")
    return [re.sub(r"(- |[0-9]+\. )", "", x, count=1) for x in elements[1:]]


def parse_card(card: dict, lists: dict) -> UserStory:
    """ Returns a UserStory object parsed from the given Trello card JSON object. 

    Arguments:
        card {dict} -- Trello card JSON object
        lists {dict} -- Mapping of Trello list ids to list objects
    
    Returns:
        UserStory - Parsed UserStory object
    """
    content = card["name"]
    desc = card["desc"].split("\n\n")
    id_ = 0 # ID is assigned later based on number of valid cards parsed
    priority = PRIORITIES[lists[card["idList"]]["name"].lower()]

    points, title, body = CARD_REGEX.match(content).groups()
    criteria = []
    notes = []
    print(desc)
    found_criteria = False
    found_notes = False

    for item in desc:
        if item.startswith('# Acceptance Criteria'):
            found_criteria = True
            found_notes = False
        elif item.startswith('# Notes'):
            found_notes = True
            found_criteria = False
        elif found_criteria:
            criteria.append(item)
        elif found_notes:
            notes.append(item)
        
        
    # print(criteria, notes)
    # if desc:
    #     criteria = parse_bullets(desc[0])
    #     if len(desc) > 1:
    #         notes = parse_bullets(desc[1])
    
    return UserStory(id_, title, body, priority, points, criteria, notes) 


def collect_lists(data: List[dict]) -> dict:
    """Returns a mapping of Trello list ids to list objects. Facilitates list lookup where only the list id is given.
    
    Arguments:
        data {List[dict]} -- Trello JSON data
    
    Returns:
        dict -- Mapping of Trello list ids to list objects
    """
    return {x["id"]:x for x in data["lists"]}


def collect_stories(filename: str) -> Tuple[List[UserStory], List[str]]:
    """Returns a list of UserStory objects extracted from the Trello JSON file having the given name, as well as a list of invalid cards.
    
    Arguments:
        filename {str} -- Name of Trello JSON file containing cards to be parsed
    
    Returns:
        List[UserStory] -- List of parsed UserStory objects
        List[str] -- Text of invalid cards that could not be parsed as UserStory objects
        List[str] -- Names of missing priority lists
    """
    with open(filename, "r", encoding='utf-8') as f:
        data = json.load(f)
    
    unsorted_cards = data["cards"]
    lists = collect_lists(data)
    stories = []
    invalid = []
    missing_lists = []
    id_ = 1

    # Check all standard priority lists exist 
    list_names = [x["name"].lower() for x in lists.values()]
    for priority in PRIORITIES:
        if priority not in list_names:
            print(f"Warning: missing \"{priority}\" list") 
            missing_lists.append(priority)

    # Sort cards according to position in board (top to bottom, left to right)
    positions = {(lists[card["idList"]]["pos"], card["pos"]):card for card in unsorted_cards}
    cards = [positions[x] for x in sorted(positions.keys())]
    
    for card in cards:
        if lists[card["idList"]]["name"].lower() not in PRIORITIES or card.get("closed", False):
            continue
        if not validate_card(card):
            print(f"Card body is not valid. Check that it has the correct format: \"{card['name']}\"")
            invalid.append(card['name'])
            continue
        try:
            story = parse_card(card, lists)
            story.id_ = str(id_)
            id_ += 1
            stories.append(story)
        except:
            print(f"Parsing failed: \"{card['name']}\"")
            invalid.append(card['name'])

    return stories, invalid, missing_lists


def main(filename: str):
    """Main process
    
    Arguments:
        filename {str} -- Name of JSON file to be converted
    """
    print("Collecting stories")
    stories, _, _ = collect_stories(filename)
    print(f"Collected {len(stories)} valid stories")
    print("Creating pptx file")
    slides.create_slides(stories, "stories.pptx")
    print("Done")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Usage: trello-convert <json-file>")
    main(sys.argv[1])
