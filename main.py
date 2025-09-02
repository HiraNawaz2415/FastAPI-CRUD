from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, computed_field
from typing import Annotated,Optional
import json
import os

app = FastAPI(
    docs_url="/doc",        # Swagger UI available at /doc
    redoc_url="/redoc"      # ReDoc available at /redoc
)

DATA_FILE = "data.json"  # file path
class Person(BaseModel):
    id: Annotated[int, Field(..., description="This is person id ")]
    name: Annotated[str, Field(..., max_length=50, description="Add person name here")]
    age: Annotated[int, Field(..., gt=0, lt=100, description="Add age of person")]
    weight: Annotated[int, Field(..., gt=10, lt=200, description="Add weight of person in kg")]
    height: Annotated[float, Field(..., gt=150, lt=200.0, description="Add height of person in cm")]

    @computed_field
    @property
    def bmi(self) -> float:
        """Calculate BMI = weight / (height^2 in meters)."""
        return round(self.weight / ((self.height / 100) ** 2), 2)
class PersonUpdate(BaseModel):
    id: Optional[Annotated[int, Field(description="This is person id ")]] = None
    name: Optional[Annotated[str, Field(max_length=50, description="Add person name here")]] = None
    age: Optional[Annotated[int, Field(gt=0, lt=100, description="Add age of person")]] = None
    weight: Optional[Annotated[int, Field(gt=10, lt=200, description="Add weight of person in kg")]] = None
    height: Optional[Annotated[float, Field(gt=150, lt=200.0, description="Add height of person in cm")]] = None

    @computed_field
    @property
    def bmi(self) -> Optional[float]:
        """Calculate BMI = weight / (height^2 in meters)."""
        if self.weight is None or self.height is None:
            return None
        return round(self.weight / ((self.height / 100) ** 2), 2)
# read data
def load_data():
    if not os.path.exists(DATA_FILE):
        return []  # if file doesn’t exist, return empty list
    with open(DATA_FILE, "r") as f:
        data = json.load(f)
    return data
# Save data
def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

@app.get("/")
def home():
    return {"message": "Welcome to JSON CRUD API "}


#  Get all records (with optional ordering and height filters)
@app.get("/users/{user_id}")
def get_users(
   user_id:int = Path(..., description="ID for Person", example="1"),
    min_height: float = Query(None, description="Filter by minimum height"),
    max_height: float = Query(None, description="Filter by maximum height"),
    order: str = Query(None, description="Order by field (age, weight, height) with 'asc' or 'desc' e.g. age:asc")
):
    data = load_data()

    # Apply height filters
    if min_height is not None:
        data = [u for u in data if u["height"] >= min_height]
    if max_height is not None:
        data = [u for u in data if u["height"] <= max_height]

    # Apply ordering
    if order:
        try:
            field, direction = order.split(":")
            if field not in ["age", "weight", "height"]:
                raise HTTPException(status_code=400, detail="Invalid order field")
            reverse = True if direction == "desc" else False
            data = sorted(data, key=lambda x: x[field], reverse=reverse)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid order format. Use field:asc or field:desc")

    return data


# Get a single user by ID
@app.get("/singleuser/{user_id}")
def get_user(user_id: int = Path(..., description="ID for Person", example="1")):
    data = load_data()
    for user in data:
        if user["id"] == user_id:
            return user
    raise HTTPException(status_code=404, detail="User not found")

# Create User Operation of CRUD
@app.post("/create")
def create_person(person: Person):
    data = load_data()

    # check if person already exists
    for existing in data:
        if existing["id"] == person.id:
            raise HTTPException(status_code=400, detail="Person already exists")

    # add new person
    new_person = person.model_dump()
    data.append(new_person)

    save_data(data)
    return JSONResponse(status_code=201, content={"message": "Person Created Successfully!"})
@app.put("/update/{person_id}")
def update_person(person_id: int, person_update: PersonUpdate):
    data = load_data()

    # Find the index of the person with this ID
    index = next((i for i, person in enumerate(data) if person["id"] == person_id), None)

    if index is None:
        raise HTTPException(status_code=404, detail="Person not exists")

    existing_person_info = data[index]

    # Update only the provided fields
    update_person_info = person_update.model_dump(exclude_unset=True)
    for key, value in update_person_info.items():
        existing_person_info[key] = value

    # Ensure ID stays the same
    existing_person_info["id"] = person_id

    # Validate with Pydantic
    person_pydantic_object = Person(**existing_person_info)
    data[index] = person_pydantic_object.model_dump()

    # Save back to file
    save_data(data)

    return JSONResponse(
        status_code=200,
        content={"message": "Person updated successfully!", "person": data[index]},
    )
@app.delete("/delete/{person_id}")
def delete_person(person_id: int):
    data = load_data()  # always load from file

    # Find person by id
    person_to_delete = None
    for person in data:
        if person["id"] == person_id:
            person_to_delete = person
            break

    if not person_to_delete:
        raise HTTPException(status_code=404, detail="Person not exists")

    # Remove from list
    data.remove(person_to_delete)

    # Save updated data back to file
    save_data(data)

    return JSONResponse(
        status_code=200,
        content={"message": f"Person with id {person_id} deleted successfully!"}
    )
