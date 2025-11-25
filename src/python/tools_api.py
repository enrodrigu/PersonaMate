from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from tools.personalDataTool import fetch_person_data, update_person_data
from tools.linkingTool import link_elements

router = APIRouter()

class PersonPayload(BaseModel):
    data: Dict[str, Any] = {}


@router.get("/tools/person/{name}")
def get_person(name: str):
    # fetch_person_data is a decorated tool; call underlying function if available
    fn = getattr(fetch_person_data, "__wrapped__", fetch_person_data)
    return fn(name)


@router.post("/tools/person/{name}")
def put_person(name: str, payload: PersonPayload):
    fn = getattr(update_person_data, "__wrapped__", update_person_data)
    # expand payload.data as kwargs - ensure keys match expected params
    return fn(name, **(payload.data or {}))


@router.post("/tools/link")
def post_link(item: Dict[str, Any]):
    a = item.get("a")
    b = item.get("b")
    rel = item.get("rel")
    if not a or not b or not rel:
        raise HTTPException(status_code=400, detail="Missing fields: a, b, rel")
    fn = getattr(link_elements, "__wrapped__", link_elements)
    return fn(a, "Person", b, "Person", rel)
