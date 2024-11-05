import json
from langchain_core.tools import tool

class Address:
    def __init__(self, street, city, state, zip):
        self.street = street
        self.city = city
        self.state = state
        self.zip = zip

class Likings:
    def __init__(self, food, sports, cinema):
        self.food = food
        self.sports = sports
        self.cinema = cinema

class Person:
    def __init__(self, name, age, email, address, likings):
        self.name = name
        self.age = age
        self.email = email
        self.address = Address(**address)
        self.likings = Likings(**likings)

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
                       zip: str = None,
                       food: list = None,
                       sports: list = None,
                       cinema: list = None) -> str:
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
        food (list, optional): List of favorite foods
        sports (list, optional): List of favorite sports
        cinema (list, optional): List of favorite cinema genres
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
            if food is not None:
                p["likings"]["food"] = food
            if sports is not None:
                p["likings"]["sports"] = sports
            if cinema is not None:
                p["likings"]["cinema"] = cinema
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
        },
        "likings": {
            "food": food,
            "sports": sports,
            "cinema": cinema
        }
    }
    data.append(new_person)
    with open('data/personal_data.json', 'w') as file:
        json.dump(data, file, indent=4)
    return "Person data added"
