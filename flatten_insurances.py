import json
import os

INPUT_FILE = "data/insurances.json"
OUTPUT_FILE = "data/insurances_flat.json"

def flatten():
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = []
    if isinstance(data, dict):
        for key in data:
            if isinstance(data[key], list):
                items.extend(data[key])
    elif isinstance(data, list):
        items = data

    flat_list = []
    for item in items:
        new_item = {
            "id": item.get("id", ""),
            "name_fa": item.get("name_fa", ""),
            "name_ar": item.get("name_ar", ""),
            "name_en": item.get("name_en", ""),
        }
        
        fields = item.get("fields", {})
        for key, val in fields.items():
            if isinstance(val, dict):
                new_item[f"{key}_fa"] = val.get("value_fa", "")
                new_item[f"{key}_ar"] = val.get("value_ar", "")
                new_item[f"{key}_en"] = val.get("value_en", "")
        
        flat_list.append(new_item)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(flat_list, f, ensure_ascii=False, indent=2)

    print(f"Success! Converted {len(flat_list)} insurances.")
    print(f"Output saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    flatten()