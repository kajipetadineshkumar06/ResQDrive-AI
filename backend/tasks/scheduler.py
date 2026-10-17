# ==========================================
# tasks/scheduler.py
# ==========================================

from apscheduler.schedulers.background import (
    BackgroundScheduler
)

from tasks.auto_assign_requests import (
    auto_assign_requests
)

from tasks.notifications import (
    send_notifications
)

from services.timeout_service import (
    recover_timed_out_requests
)


# ==========================================
# SCHEDULER
# ==========================================

scheduler = BackgroundScheduler()


# ==========================================
# START SCHEDULER
# ==========================================

def start_scheduler():

    if scheduler.running:

        return

    # ==========================================
    # AUTO ASSIGN
    # ==========================================

    scheduler.add_job(

        auto_assign_requests,

        trigger="interval",

        seconds=30,

        id="auto_assign",

        replace_existing=True,

        max_instances=1,

        coalesce=True
    )

    # ==========================================
    # TIMEOUT RECOVERY
    # ==========================================
    #
    # Runs every 5 seconds.
    #
    # This is the important restart-safe part.
    #
    # If Uvicorn restarts:
    #
    #     old timeout thread disappears
    #
    # but:
    #
    #     database still contains requested_at
    #
    # Therefore the scheduler can recover it.
    #
    # ==========================================

    scheduler.add_job(

        recover_timed_out_requests,

        trigger="interval",

        seconds=5,

        id="timeout_recovery",

        replace_existing=True,

        max_instances=1,

        coalesce=True
    )

    # ==========================================
    # NOTIFICATIONS
    # ==========================================

    scheduler.add_job(

        send_notifications,

        trigger="interval",

        minutes=1,

        id="notifications",

        replace_existing=True,

        max_instances=1,

        coalesce=True
    )

    # ==========================================
    # START
    # ==========================================

    scheduler.start()

    print(
        "✅ Scheduler Started"
    )

    print(
        "⏱️ Timeout recovery enabled "
        "(every 5 seconds)"
    )


# ==========================================
# STOP SCHEDULER
# ==========================================

def stop_scheduler():

    if scheduler.running:

        scheduler.shutdown(
            wait=False
        )

        print(
            "🛑 Scheduler Stopped"
        )