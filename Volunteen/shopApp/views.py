from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.db.models import Sum, F
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .forms import IdentifyChildForm
from .models import Shop, Redemption, Reward
from childApp.models import Child
from teenApp.utils import NotificationManager  
import json
from datetime import datetime
import random
from .serializers import RewardSerializer, ShopSerializer, RedemptionSerializer
from django.db.models.functions import TruncMonth

class ShopRedeemPointsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch the shop associated with the logged-in user
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=404)

        # Calculate the remaining points for the shop
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        remaining_points = shop.max_points - points_used_this_month

        # Filter rewards that can be redeemed
        rewards = Reward.objects.filter(
            shop=shop,
            points_required__lte=remaining_points
        )

        # Serialize rewards
        serialized_rewards = RewardSerializer(rewards, many=True).data

        return Response({
            "remaining_points": remaining_points,
            "rewards": serialized_rewards,
        })

    def post(self, request):
        # Handle selected rewards submission
        selected_rewards = request.data.get('selected_rewards')
        if not selected_rewards:
            return Response({"error": "No rewards selected."}, status=400)

        # Store selected rewards in the session
        request.session['selected_rewards'] = json.dumps(selected_rewards)

        # Redirect to the next step (identifying the child)
        return Response({"message": "Rewards selected successfully. Proceed to identify child."})


class ShopIdentifyChildView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        form = IdentifyChildForm(data=request.data)

        if form.is_valid():
            identifier = form.cleaned_data['identifier']
            secret_code = form.cleaned_data['secret_code']

            try:
                child = Child.objects.get(identifier=identifier, secret_code=secret_code)
                # Update secret code
                child.secret_code = get_random_digits()
                child.save()

                # Store child_id in the session (or return it in the response)
                request.session['child_id'] = child.id

                return Response({
                    "message": "Child identified successfully.",
                    "child_id": child.id,
                })
            except Child.DoesNotExist:
                return Response({"error": "Invalid identifier or secret code."}, status=404)

        return Response({"error": "Invalid data.", "details": form.errors}, status=400)
    
    
class ShopCompleteTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Retrieve child_id and selected_rewards from session
        child_id = request.session.get('child_id')
        if not child_id:
            return Response({"error": "Child not identified."}, status=400)

        selected_rewards_json = request.session.get('selected_rewards')
        if not selected_rewards_json:
            return Response({"error": "No rewards selected."}, status=400)

        selected_rewards = json.loads(selected_rewards_json)
        child = get_object_or_404(Child, id=child_id)
        shop = get_object_or_404(Shop, user=request.user)

        # Calculate points used this month and remaining points
        start_of_month = now().replace(day=1)
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0
        remaining_points = shop.max_points - points_used_this_month

        # Calculate total points for the selected rewards
        total_points = sum(r['quantity'] * r['points'] for r in selected_rewards)

        if child.points >= total_points and total_points <= remaining_points:
            points_used = 0
            for reward in selected_rewards:
                reward_obj = get_object_or_404(Reward, id=reward['reward_id'])
                points_used += reward['quantity'] * reward['points']
                child.subtract_points(reward['quantity'] * reward['points'])
                Redemption.objects.create(
                    child=child,
                    points_used=reward['quantity'] * reward['points'],
                    shop=reward_obj.shop,
                )

            # Clear session data
            request.session['selected_rewards'] = json.dumps([])
            request.session.pop('child_id', None)

            # Send notification if email exists
            if child.user.email:
                NotificationManager.sent_mail(
                    f'Dear {child.user.first_name}, your redemption is complete. You have redeemed {points_used} points.',
                    child.user.email,
                )

            return Response({
                "message": "Redemption completed successfully.",
                "points_used": points_used,
                "receipt": selected_rewards,
            })

        return Response({"error": "Not enough points or exceeding shop's monthly limit."}, status=400)
    
class ShopCancelTransactionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Clear session data
        request.session.pop('child_id', None)
        request.session['selected_rewards'] = json.dumps([])
        return Response({"message": "Transaction cancelled successfully."})

class ShopHomeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Fetch the shop associated with the logged-in user
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=404)

        # Calculate start of the current month
        start_of_month = now().replace(day=1)

        # Filter redemptions for the current month
        redemptions_this_month = Redemption.objects.filter(shop=shop, date_redeemed__gte=start_of_month)

        # Calculate total points used this month
        points_used_this_month = redemptions_this_month.aggregate(total_points=Sum('points_used'))['total_points'] or 0

        # Calculate points left to redeem
        points_left_to_redeem = max(0, shop.max_points - points_used_this_month)

        # Serialize the shop object for response
        serialized_shop = ShopSerializer(shop).data

        return Response({
            "shop": serialized_shop,
            "points_used_this_month": points_used_this_month,
            "points_left_to_redeem": points_left_to_redeem,
        })

def get_random_digits(n=3):
    return ''.join(str(random.randint(0, 9)) for _ in range(n))

class ShopRedemptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # Get the shop associated with the logged-in user
            shop = Shop.objects.get(user=request.user)
        except Shop.DoesNotExist:
            return Response({"error": "Shop not found"}, status=404)

        # Get all redemptions for the shop
        redemptions = Redemption.objects.filter(shop=shop).order_by('-date_redeemed')

        # Aggregate monthly redemption points
        monthly_redemptions = (
            redemptions.annotate(month=TruncMonth('date_redeemed'))
                       .values('month')
                       .annotate(
                           total_points=Sum('points_used'),
                           max_points=F('shop__max_points')
                       )
                       .order_by('-month')
        )

        # Serialize the last 10 redemptions
        recent_redemptions = redemptions[:10]
        serialized_recent_redemptions = RedemptionSerializer(recent_redemptions, many=True).data

        return Response({
            "shop_name": shop.name,
            "monthly_redemptions": list(monthly_redemptions),  # Convert queryset to list
            "recent_redemptions": serialized_recent_redemptions,
        })
        


class ToggleRewardVisibilityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, reward_id):
        # Fetch the reward and ensure the user is the shop owner
        reward = get_object_or_404(Reward, id=reward_id)

        if request.user == reward.shop.user:
            # Toggle the visibility
            reward.is_visible = not reward.is_visible
            reward.save()

            return Response({"success": True, "is_visible": reward.is_visible})

        return Response({"success": False, "error": "Forbidden"}, status=403)