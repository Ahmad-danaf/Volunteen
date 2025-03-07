import os
from childApp.utils import medal_criteria
import json
from childApp.models import Medal

def load_medals_from_json():
    """
    Load medal definitions from a JSON file and create or update Medal objects in the database.
    """
    file_path = os.path.join(os.path.dirname(__file__), './utils/data/medals.json')
    with open(file_path, 'r', encoding='utf-8') as f:
        medals_data = json.load(f)
    
    for medal_data in medals_data:
        Medal.objects.update_or_create(
            name=medal_data['name'],
            defaults={
                'description': medal_data['description'],
                'points_reward': medal_data['points_reward'],
                'criterion': medal_data['criterion']
            }
        )
#load_medals_from_json()

def check_and_award_medals(child):
    medals = Medal.objects.all()
    awarded_medals = []
    
    for medal in medals:
        criterion_function = getattr(medal_criteria, medal.criterion, None)
        if criterion_function and criterion_function(child):
            if not child.medals.filter(id=medal.id).exists():
                child.medals.add(medal)
                child.points += medal.points_reward
                child.save()
                awarded_medals.append(medal)
    
    return awarded_medals
from asgiref.sync import sync_to_async

async def check_and_award_medals_async(child):
    return await sync_to_async(check_and_award_medals)(child)
