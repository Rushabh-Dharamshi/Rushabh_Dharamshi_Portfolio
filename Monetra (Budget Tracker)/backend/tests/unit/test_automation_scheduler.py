import types

from budget_tracker_api.services.automation_scheduler import AutomationScheduler


class FakeAutomationService:
    def __init__(self, fail=False):
        self.fail = fail
        self.upcoming_calls = 0
        self.month_end_calls = 0

    def run_upcoming_bills_email_if_due(self, recipient=None):
        self.upcoming_calls += 1
        if self.fail:
            raise RuntimeError("boom")

    def run_month_end_email_if_due(self, recipient=None):
        self.month_end_calls += 1


class FakeAppContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FakeApp:
    def __init__(self, service):
        self.extensions = {"services": {"automation_service": service}}

    def app_context(self):
        return FakeAppContext()


class FakeThread:
    def __init__(self, target, name, daemon):
        self.target = target
        self.name = name
        self.daemon = daemon
        self.started = False
        self.joined = False

    def start(self):
        self.started = True

    def is_alive(self):
        return self.started and not self.joined

    def join(self, timeout=None):
        self.joined = True


def test_scheduler_start_and_stop(monkeypatch):
    created = []

    def fake_thread(target, name, daemon):
        thread = FakeThread(target, name, daemon)
        created.append(thread)
        return thread

    monkeypatch.setattr("budget_tracker_api.services.automation_scheduler.Thread", fake_thread)
    scheduler = AutomationScheduler(FakeApp(FakeAutomationService()), poll_seconds=10)

    scheduler.start()
    scheduler.start()
    assert len(created) == 1
    assert created[0].started is True

    scheduler.stop()
    assert created[0].joined is True


def test_scheduler_loop_runs_once():
    service = FakeAutomationService()
    scheduler = AutomationScheduler(FakeApp(service), poll_seconds=120)

    class StopEvent:
        def __init__(self):
            self.calls = 0

        def is_set(self):
            return self.calls > 0

        def wait(self, timeout):
            self.calls += 1
            return True

        def set(self):
            self.calls = 99

    scheduler._stop_event = StopEvent()
    scheduler._run_loop()

    assert service.upcoming_calls == 1
    assert service.month_end_calls == 1
    assert scheduler._next_realtime_run_at is not None


def test_scheduler_loop_swallow_exceptions():
    service = FakeAutomationService(fail=True)
    scheduler = AutomationScheduler(FakeApp(service), poll_seconds=120)

    class StopEvent:
        def __init__(self):
            self.calls = 0

        def is_set(self):
            return self.calls > 0

        def wait(self, timeout):
            self.calls += 1
            return True

        def set(self):
            self.calls = 99

    scheduler._stop_event = StopEvent()
    scheduler._run_loop()

    assert service.upcoming_calls == 1


def test_scheduler_helper_methods():
    scheduler = AutomationScheduler(FakeApp(FakeAutomationService()), poll_seconds=900)
    assert scheduler._poll_seconds == 900
    assert scheduler._should_run_realtime(types.SimpleNamespace()) is True

    now = __import__("datetime").datetime.now()
    scheduler._next_realtime_run_at = now
    assert scheduler._should_run_realtime(now) is True
    assert scheduler._should_run_month_end_minute(now) is True
    assert scheduler._should_run_month_end_minute(now) is False
    assert scheduler._seconds_until_next_wake(now) >= 1.0
