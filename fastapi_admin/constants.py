import pathlib

BASE_DIR = pathlib.Path(__file__).resolve().parent
# time format
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
DATE_FORMAT = "%Y-%m-%d"

# MOMENT - js library for filter datetimes range
DATETIME_FORMAT_MOMENT = "YYYY-MM-DD HH:mm:ss"
DATE_FORMAT_MOMENT = "YYYY-MM-DD"

# flatpickr settings - js library for input datetime
DATE_FORMAT_FLATPICKR = "Y-m-d"

# redis cache
CAPTCHA_ID = "captcha:{captcha_id}"
LOGIN_ERROR_TIMES = "login_error_times:{ip}"
LOGIN_USER = "login_user:{token}"

# i18n
PATH_TO_LOCALES = BASE_DIR / "locales"
