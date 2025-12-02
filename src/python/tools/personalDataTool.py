import json
import re
import unicodedata

from langchain_core.tools import tool
from utils.neo4j_graph import Neo4jGraph


def _normalize_name(name: str) -> str:
    """Normalize a name for matching: strip, lowercase, remove diacritics and punctuation,
    collapse whitespace."""
    if not name:
        return ""
    s = name.strip()
    # NFKD normalize and remove diacritics
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # Lowercase
    s = s.lower()
    # Replace non-alphanumeric with space
    s = re.sub(r"[^0-9a-z]+", " ", s)
    # Collapse spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


@tool
def fetch_person_data(name: str) -> str:
    """Fetch personal information about a person by name from Neo4j.

    Returns a dict with node properties and a `graph_context` key containing neighbor info.
    """
    if not name:
        return "Person not found"

    norm = _normalize_name(name)
    g = Neo4jGraph.load()
    try:
        # Perform case-insensitive lookup by comparing normalized forms
        # We store and compare against the original `name` property but match using toLower
        query = "MATCH (p:Person) WHERE toLower(p.name) = $lower RETURN p LIMIT 1"
        with g._driver.session(database=g._database) as session:
            rec = session.run(query, lower=name.lower()).single()
            if rec:
                node = rec.get("p")
                props = dict(node)
            else:
                # Fallback: fetch all Person names and compare normalized forms locally
                results = session.run("MATCH (p:Person) RETURN p.name as name, p as p")
                props = None
                for r in results:
                    candidate = r.get("name")
                    if _normalize_name(candidate) == norm:
                        props = dict(r.get("p"))
                        break
                if not props:
                    return "Person not found"

        # Parse JSON address if it exists
        if "address" in props and isinstance(props["address"], str):
            try:
                props["address"] = json.loads(props["address"])
            except (json.JSONDecodeError, TypeError):
                pass  # Keep as string if parsing fails

        # Enrich with neighbors
        neighbors = g.get_neighbors(props.get("name"), "Person")
        props["graph_context"] = neighbors
        return props
    finally:
        try:
            g.close()
        except Exception:
            pass


@tool
def update_person_data(
    name: str,
    age: int = None,
    email: str = None,
    street: str = None,
    city: str = None,
    state: str = None,
    zip: str = None,
) -> str:
    """Create or update a Person node in Neo4j with the provided properties.

    Address fields are stored as a map in the `address` property.
    """
    if not name:
        return "Name is required"

    g = Neo4jGraph.load()
    try:
        # Build address map
        address = {}
        if street is not None:
            address["street"] = street
        if city is not None:
            address["city"] = city
        if state is not None:
            address["state"] = state
        if zip is not None:
            address["zip"] = zip

        params = {"name": name}
        set_clauses = []
        if age is not None:
            set_clauses.append("p.age = $age")
            params["age"] = age
        if email is not None:
            set_clauses.append("p.email = $email")
            params["email"] = email
        if address:
            # Store address as JSON string since Neo4j doesn't support map properties directly
            set_clauses.append("p.address = $address")
            params["address"] = json.dumps(address)

        # MERGE node and set properties
        if set_clauses:
            set_stmt = ", ".join(set_clauses)
            query = f"MERGE (p:Person {{name: $name}}) SET {set_stmt} RETURN p"
        else:
            query = "MERGE (p:Person {name: $name}) RETURN p"

        with g._driver.session(database=g._database) as session:
            result = session.run(query, **params)
            # Consume the result to ensure transaction commits
            result.single()
        return "Person data updated"
    finally:
        try:
            g.close()
        except Exception:
            pass
