import json

def remove_phone_from_backup(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        fields = item.get('fields', {})

        # שלב 1: הסרת המפתח "phone" מ־auth.user
        if item.get('model') == 'auth.user':
            if 'phone' in fields:
                del fields['phone']

        # שלב 2: הסרת האזכור "Phone" מ־change_message (אם מופיע) 
        # למשל: "[{\"changed\": {\"fields\": [\"Phone\"]}}]"
        change_message = fields.get('change_message')
        if change_message:
            try:
                # מנסים לעשות parse ל־JSON בתוך המחרוזת של change_message
                parsed_message = json.loads(change_message)
                
                # לפי הדוגמה זה עשוי להיות list של dict,
                # לדוגמה: [{"changed": {"fields": ["Phone"]}}]
                if isinstance(parsed_message, list):
                    for subitem in parsed_message:
                        changed_part = subitem.get('changed')
                        if isinstance(changed_part, dict) and 'fields' in changed_part:
                            fields_list = changed_part['fields']
                            if isinstance(fields_list, list) and "Phone" in fields_list:
                                changed_part['fields'] = [f for f in fields_list if f != "Phone"]
                
                # משחזרים חזרה ל־JSON ומעדכנים ב־fields
                fields['change_message'] = json.dumps(parsed_message, ensure_ascii=False)

            except json.JSONDecodeError:
                # אם לא הצליח לעשות parse ל־change_message, מתעלמים
                pass

    # שמירה של התוצאה בקובץ חדש
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# דוגמה לשימוש:
if __name__ == "__main__":
    remove_phone_from_backup("adjusted_backup.json", "backup_no_phone.json")
    print("הקובץ החדש נשמר בהצלחה כ- backup_no_phone.json")
