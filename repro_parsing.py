from backend.engine.text_to_specs_v2 import ProximityLayoutGenerator
import json

architect = ProximityLayoutGenerator()

prompt = "I want a modern 2400 square feet 2BHK house. The living room should be the central space, around 600 square feet, and connected to the dining area and a balcony. The dining area should be about 300 square feet and located between the living room and kitchen. The kitchen should be 250 square feet and connected to a utility room of 100 square feet. The master bedroom should be 400 square feet with an attached bathroom of 150 square feet and located in a private corner of the house. The second bedroom should be 300 square feet with easy access to a common bathroom of 150 square feet. There should also be a small study room of 200 square feet connected to the living room. Ensure proper circulation space and logical room connections."

total_area, rooms, used_area, excluded = architect.parse_natural_language(prompt)

output = {
    "total_area": total_area,
    "rooms": rooms,
    "mentions": architect._find_room_mentions(prompt)
}

with open("output.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("Done.")
