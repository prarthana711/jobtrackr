"""Send every reminder that is due, once, then exit.

Run from the backend folder:   python -m scripts.send_reminders

Use this instead of the in-app loop when something else runs it on a schedule,
for example Windows Task Scheduler, cron, or a hosting service's scheduled job.
"""
import logging

from app.services.scheduler import run_reminder_check


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    result = run_reminder_check()
    print(f"Reminders sent: {result['sent']}, failed: {result['failed']}")


if __name__ == "__main__":
    main()