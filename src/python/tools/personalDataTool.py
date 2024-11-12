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
    data = load_person_data('data/personal_data.json')
    if not data:
        return "No data found"
    for person in data:
        if person["name"].lower() == name.lower():
            return person
    return "Person not found"

@tool
def update_person_data(name: str,
                       age: int = None,
                       email: str = None,
                       street: str = None,
                       city: str = None,
                       state: str = None,
                       zip: str = None) -> str:
    """
    Update personal information about a person regarding their name

    Args:
        name (str): Name of the person
        age (int, optional): Age of the person
        email (str, optional): Email of the person
        street (str, optional): Street address of the person
        city (str, optional): City of the person
        state (str, optional): State of the person
        zip (str, optional): Zip code of the person
    """
    data = load_person_data('data/personal_data.json')
    for p in data:
        if p["name"].lower() == name.lower():
            if age is not None:
                p["age"] = age
            if email is not None:
                p["email"] = email
            if street is not None:
                p["address"]["street"] = street
            if city is not None:
                p["address"]["city"] = city
            if state is not None:
                p["address"]["state"] = state
            if zip is not None:
                p["address"]["zip"] = zip
            with open('data/personal_data.json', 'w') as file:
                json.dump(data, file, indent=4)
            return "Person data updated"
    new_person = {
        "name": name,
        "age": age,
        "email": email,
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "zip": zip
        }
    }
    data.append(new_person)
    with open('data/personal_data.json', 'w') as file:
        json.dump(data, file, indent=4)
    return "Person data added"
