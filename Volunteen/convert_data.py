import json

# Load the JSON file
with open('db.json', 'r') as file:
    data = json.load(file)

# Map old model names to new model names
model_mapping = {
    "teenApp.child": "childApp.child",
    "teenApp.mentor": "mentorApp.mentor",
    "teenApp.shop": "shopApp.shop",
    "teenApp.reward": "shopApp.reward",
    "teenApp.redemption": "shopApp.redemption"
    # Add other mappings as needed
}

# Update the model names
for entry in data:
    if entry['model'] in model_mapping:
        entry['model'] = model_mapping[entry['model']]

# Save the updated JSON
with open('adjusted_backup.json', 'w') as file:
    json.dump(data, file, indent=4)

print("Model names updated successfully!")
