import json
from langchain_core.tools import tool

def load_person_data(file_path):
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

@tool
def fetch_person_data(name: str) -> str:
    """
    Fetch personal information about a person regarding their name
    """
    data = load_person_data('../personal_data.json')
    for person in data:
        if person["name"].lower() == name.lower():
            return person
    return "Person not found"