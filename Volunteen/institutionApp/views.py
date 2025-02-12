from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Institution, TeencoinsTransfer
from mentorApp.models import Mentor
from django.db.models import Sum, Q

@login_required
def institution_home(request):
    """
    Displays the institution dashboard with mentors, balances, and transfer history.
    """
    institution = get_object_or_404(Institution, manager=request.user)
    mentors = institution.mentors.all()
    transfers = []  # Placeholder for transfer history, implement when ready

    return render(request, 'institution_home.html', {
        'institution': institution,
        'mentors': mentors,
        'transfers': transfers
    })

@csrf_exempt
@login_required
def transfer_teencoins_to_mentor(request):
    """
    Transfers Teencoins from the institution to a mentor and logs the transaction.
    """
    institution = get_object_or_404(Institution, manager=request.user)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        mentor_id = data.get('mentor_id')
        amount = int(data.get('amount', 0))

        mentor = get_object_or_404(Mentor, id=mentor_id)

        try:
            institution.allocate_teencoins_to_mentor(mentor, amount)

            # Log the transfer
            TeencoinsTransfer.objects.create(
                institution=institution,
                sender=None,  # No sender means the institution is sending
                receiver=mentor,
                amount=amount
            )

            return JsonResponse({'message': f'Successfully transferred {amount} Teencoins to {mentor.user.username}.'})
        except ValueError as e:
            return JsonResponse({'message': str(e)}, status=400)

    # Get mentors list for dropdown
    mentors = institution.mentors.all()
    return render(request, 'transfer_teencoins.html', {'institution': institution, 'mentors': mentors})

@csrf_exempt
@login_required
def transfer_between_mentors(request):
    """
    Transfers Teencoins from one mentor to another and logs the transaction.
    """
    institution = get_object_or_404(Institution, manager=request.user)
    mentors = institution.mentors.all()

    if request.method == 'POST':
        data = json.loads(request.body)
        mentor_from_id = data.get('mentor_from')
        mentor_to_id = data.get('mentor_to')
        amount = int(data.get('amount', 0))

        mentor_from = get_object_or_404(Mentor, id=mentor_from_id, institutions=institution)
        mentor_to = get_object_or_404(Mentor, id=mentor_to_id, institutions=institution)

        if amount <= 0 or amount > mentor_from.available_teencoins:
            return JsonResponse({'message': 'Invalid amount or insufficient balance.'}, status=400)

        # Update balances
        mentor_from.available_teencoins -= amount
        mentor_to.available_teencoins += amount
        mentor_from.save()
        mentor_to.save()

        # Log the transfer
        TeencoinsTransfer.objects.create(
            institution=institution,
            sender=mentor_from,
            receiver=mentor_to,
            amount=amount
        )

        return JsonResponse({'message': f'Successfully transferred {amount} Teencoins from {mentor_from.user.username} to {mentor_to.user.username}.'})

    return render(request, 'transfer_between_mentors.html', {
        'institution': institution,
        'mentors': mentors
    })


@login_required
def get_transfer_history(request):
    """
    Retrieves and displays the institution's transfer history.
    """
    institution = get_object_or_404(Institution, manager=request.user)

    # Retrieve transfers related to the institution
    transfers = TeencoinsTransfer.objects.filter(
        institution=institution
    ).order_by('-timestamp')

    return render(request, 'transfer_history.html', {
        'institution': institution,
        'transfers': transfers
    })



@login_required
def get_balances(request):
    """
    Returns institution balance and mentor balances.
    """
    institution = get_object_or_404(Institution, manager=request.user)

    mentor_balances = [
        {
            'mentor': mentor.user.username,
            'available_teencoins': mentor.available_teencoins,
        }
        for mentor in institution.mentors.all()
    ]

    return JsonResponse({
        'total_teencoins': institution.total_teencoins,
        'available_teencoins': institution.available_teencoins,
        'mentors': mentor_balances
    })

def institution_balances(request):
    # Query your Institution model, or wherever you store balances
    institution = ...  # get or compute institution object
    data = {
        'total_teencoins': institution.total_teencoins,
        'available_teencoins': institution.available_teencoins,
    }
    return JsonResponse(data)


@login_required
def mentor_management(request):
    institution = get_object_or_404(Institution, manager=request.user)
    mentors = institution.mentors.all()

    return render(request, 'mentor_management.html', {
        'institution': institution,
        'mentors': mentors
    })
