from django.contrib import messages
from django.shortcuts import render, redirect
from managementApp.decorators import superadmin_required
from managementApp.utils.superadmin_utils import SuperAdminUtility

from django.shortcuts import render
from managementApp.decorators import superadmin_required

@superadmin_required
def upload_menu_view(request):
    """
    SuperAdmin upload menu that lets them choose between
    uploading children, mentors, shops, or institutions via CSV.
    """
    upload_options = [
        {
            "title": "העלאת ילדים מקובץ CSV",
            "icon_color": "indigo-400",
            "url_name": "managementApp:upload_children_csv",
            "svg_path": "M12 4v16m8-8H4"
        },
        {
            "title": "העלאת מנטורים",
            "icon_color": "blue-400",
            "url_name": "managementApp:coming_soon",
            "svg_path": "M5.121 17.804A7.963 7.963 0 0112 16c1.657 0 3.182.506 4.379 1.362"
        },
        {
            "title": "העלאת מוסדות",
            "icon_color": "green-400",
            "url_name": "managementApp:coming_soon",  
            "svg_path": "M3 10h18M5 6h14M7 14h10"
        },
        {
            "title": "העלאת חנויות",
            "icon_color": "pink-400",
            "url_name": "managementApp:coming_soon",
            "svg_path": "M3 3h18v6H3z M5 9v12h14V9"
        }
    ]
    
    return render(request, "superadmin/upload_menu.html", {"upload_options": upload_options})



@superadmin_required
def upload_children_csv(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file or not csv_file.name.endswith(".csv"):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect("managementApp:upload_children_csv")

        rows = SuperAdminUtility.parse_csv(csv_file)
        logs = []
        total_rows = 0
        total_created_children = 0
        total_skipped_children = 0
        total_created_subscriptions = 0
        total_updated_subscriptions = 0
        total_non_provided_subscriptions = 0
        for i, row in enumerate(rows, start=2):
            total_rows += 1
            success, log = SuperAdminUtility.create_child_from_row(row)
            log["row"] = i-1
            logs.append(log)
            
            if log.get("created_user", False):                     
                total_created_children += 1
            else:
                total_skipped_children += 1
            if log.get("subscription_action") == "Created":
                total_created_subscriptions += 1
            elif log.get("subscription_action") == "Updated":
                total_updated_subscriptions += 1
            elif log.get("subscription_action") == "Not provided":
                total_non_provided_subscriptions += 1
                
        context = {
            "logs": logs,
            "summary": {
                "total_rows": total_rows,
                "total_created_children": total_created_children,
                "total_skipped_children": total_skipped_children,
                "total_created_subscriptions": total_created_subscriptions,
                "total_updated_subscriptions": total_updated_subscriptions,
                "total_non_provided_subscriptions": total_non_provided_subscriptions,
            }
        }
        return render(request, "superadmin/upload_child_users.html", context)

    return render(request, "superadmin/upload_child_users.html")


@superadmin_required
def superadmin_dashboard(request):
    """
    Render the Super Admin dashboard.
    """
    return render(request, "superadmin/superadmin_dashboard.html")


@superadmin_required
def coming_soon(request):
    """
    Render a 'Coming Soon' page for the Super Admin.
    """
    return render(request, "feature_not_completed.html")