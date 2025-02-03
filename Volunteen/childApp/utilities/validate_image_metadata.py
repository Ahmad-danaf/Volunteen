from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import datetime

def validate_image_metadata(image):
    try:
        img = Image.open(image)
        exif_data = img._getexif()

        if not exif_data:
            return False, "לא נמצאו נתוני EXIF בתמונה."

        exif = {TAGS.get(tag): value for tag, value in exif_data.items() if tag in TAGS}

        datetime_original = exif.get("DateTimeOriginal")
        if datetime_original:
            photo_time = datetime.datetime.strptime(datetime_original, "%Y:%m:%d %H:%M:%S")
            current_time = datetime.datetime.now()

            if (current_time - photo_time).total_seconds() > 3600:
                return False, "התמונה צולמה לפני זמן רב מדי."

        return True, "התמונה תקינה."
    except Exception as e:
        return False, f"שגיאה בבדיקת נתוני התמונה: {str(e)}"
