import http.client
import json
import os

import requests
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.text import slugify
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import exception_handler as drf_exception_handler

app_name = "Auction-App"


def create_error_data(msg):
    msg = [msg]
    error_data = {"errors": msg}
    return error_data


def create_message_data(msg):
    msg = msg
    error_data = {"message": msg}
    return error_data


def email_compose(type, data=False):
    emailContent = ""
    subject = ""
    if type == "reset-password":
        emailContent = f"<div style='text-align: center'><p style='font-size: 16px; text-align: center; font-weight: bold'>HI, {data.name} <p>There was a request to change your password!</p><p>If you did not make this request, just ignore this email. Otherwise, please enter the code below to reset your password</p><h2 style='color: black'>{data.code}</h2></div>"
        subject = f"{app_name} Password Reset"
    elif type == "welcome":
        emailContent = f"<div style='text-align: left'><img src='https://hdxdev-spaces.nyc3.digitaloceanspaces.com/ayinle-api-static/assets/logo.png' width='200px' /><div style='font-size: 16px; text-align: left; font-weight: bold'>Hey, {data.name} </div> <div>Welcome to the Conapp Family</div><div>We are happy to have you on board with other creative proffesionals.</div><div>Login and have fun using Conapp</div><p>You can contact us <a href='https://ayinle.com/contact'>here</a> or call 055 035 9588 to get quick answers to your questions .</p><img src='https://hdxdev-spaces.nyc3.digitaloceanspaces.com/ayinle-api-static/assets/headImage.jpg' width='500px' /></div>"
        subject = f"Welcome to {app_name}"
    elif type == "test":
        emailContent = "<p>Test Mail</p>"
        subject = f"{app_name} Test mail"

    data = {"emailContent": emailContent, "subject": subject}
    return data


def send_mail(email, subject, value, type="text/html"):
    conn = http.client.HTTPSConnection("rapidprod-sendgrid-v1.p.rapidapi.com")

    payload = {
        "personalizations": [{"to": [{"email": email}], "subject": subject}],
        "from": {"email": "contact@conapp.com", "name": "Conapp"},
        "content": [{"type": type, "value": value}],
    }
    # payload = payload.format(email=email, subject=subject, type=type, value=value)
    headers = {
        "content-type": "application/json",
        "x-rapidapi-key": os.environ.get("RAPID_API_KEY"),
        "x-rapidapi-host": "rapidprod-sendgrid-v1.p.rapidapi.com",
    }

    conn.request("POST", "/mail/send", json.dumps(payload), headers)

    res = conn.getresponse()
    data = res.read()


def send_mail_mailgun(email, subject, value, type="text/html"):
    mail_domain = os.environ.get("MAIL_DOMAIN")
    return requests.post(
        f"https://api.mailgun.net/v3/{mail_domain}/messages",
        auth=("api", os.environ.get("MAILGUN_API_KEY")),
        data={
            "from": f"HDXDEV <contact@hdxdev.tech>",
            "to": [email],
            "subject": subject,
            "html": value,
        },
    )


def mock_if_true():
    return False


def custom_exception_handler(exc, context):
    """Handle Django ValidationError as an accepted exception"""

    if isinstance(exc, DjangoValidationError):
        if hasattr(exc, "message_dict"):
            exc = DRFValidationError(detail={"error": exc.message_dict})
        elif hasattr(exc, "message"):
            exc = DRFValidationError(detail={"error": exc.message})
        elif hasattr(exc, "messages"):
            exc = DRFValidationError(detail={"error": exc.messages})

    return drf_exception_handler(exc, context)


def return_constants():
    base_url = "https://hdxdev-spaces.nyc3.digitaloceanspaces.com"
    images_url = f"{base_url}/ayinle-api-static/assets"

    constants = {"imagesUrlDefault": f"{images_url}/default.png"}
    return constants


def clean_url(text, id=0):
    title = slugify(text)
    if id:
        title = f"{title}_{id}"
    return title


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 1000


class StandardAdminResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 1000
