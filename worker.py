# worker.py

from app import app, scheduler
import time

if __name__ == "__main__":
    with app.app_context():
        print("🚀 Starting FitAura Background Scheduler (APScheduler)...")

        # Start the scheduler from your app
        scheduler.start()

        print("⏳ Scheduler started and running...")

        # Prevent script from exiting
        try:
            while True:
                time.sleep(60)  # keep the process alive
        except KeyboardInterrupt:
            print("🛑 Scheduler stopped.")
