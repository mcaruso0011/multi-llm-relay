class RelayManager:
    def __init__(self):
        self.paused = False
        self.active_task = None
        self.buffer = ""

    def start_task(self, task_id):
        self.active_task = task_id
        self.buffer = ""
        self.paused = False

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False
        return self.buffer # Use existing context to continue

relay_manager = RelayManager()