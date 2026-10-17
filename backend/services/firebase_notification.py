from firebase_admin import messaging

from models.fcm_token import FCMToken


def send_push_notification(
    db,
    user_id: int,
    title: str,
    body: str,
    data: dict = None
):
    """
    Send Firebase Push Notification
    """

    token = db.query(
        FCMToken
    ).filter(
        FCMToken.user_id == user_id
    ).first()

    if not token:
        print("No FCM token found.")
        return False

    message = messaging.Message(

        notification=messaging.Notification(
            title=title,
            body=body
        ),

        token=token.token,

        data=data or {}

    )

    try:

        response = messaging.send(message)

        print("Push notification sent.")

        return True

    except Exception as e:

        print("Firebase push notification failed.")

        return False