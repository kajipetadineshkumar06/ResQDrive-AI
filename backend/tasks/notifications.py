# ==========================================
# ResQDrive AI
# Notification Background Task
# ==========================================

from database import SessionLocal

from models.notification import Notification


def send_notifications():
    db = SessionLocal()

    try:
        notifications = (
            db.query(Notification)
            .filter(
                Notification.status == "unread"
            )
            .all()
        )

        if len(notifications) == 0:
            print("No unread notifications.")
            return

        for notification in notifications:

            print(
                f"📩 Processing Notification "
                f"{notification.notification_id}"
            )

            print(
                f"Title   : {notification.title}"
            )

            print(
                f"Message : {notification.message}"
            )

            # -------------------------------------
            # Notification processing
            #
            # Future integrations:
            # - Send Email
            # - Send SMS
            # - Send Firebase Push Notification
            #
            # IMPORTANT:
            # Do NOT change the status here.
            #
            # "unread" means the notification has
            # not been read by the user.
            #
            # "read" means the user has read it.
            #
            # There is currently no separate
            # "sent" status required for this task.
            # -------------------------------------

        db.commit()

        print(
            "✅ Notifications processed successfully."
        )

    except Exception as e:

        db.rollback()

        print(
            "Notification Error:",
            e
        )

    finally:

        db.close()