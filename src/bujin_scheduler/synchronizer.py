#
# The idea of this module is to offer basic
# reconcilation of todos events in a calendar
# managed by us.
# We have two rules:
# (a) We kill every calendar item that collides with another one, if it's managed by us.
# (b) We don't repeat ourselves if the calendar item target is the right one by comparing fingerprints.
# Fingerprint is defined as the hash of the iCalendar object.
import caldav
from collections import defaultdict
from .scheduler import ScheduleItem
from datetime import timedelta

class TodoSynchronizationPlan:
    def __init__(self, steps: list):
        self.steps = steps
        pass

    def apply(self, calendar: caldav.Calendar):
        for step in self.steps:
            step.apply(calendar)

    def diagnose(self):
        for step in self.steps:
            if isinstance(step, AddStep):
                print(f'Adding {step}')
            elif isinstance(step, DeleteStep):
                print(f'Removing {step}')

class AddStep:
    def __init__(self, item: ScheduleItem):
        self.item = item

    @property
    def todo_args(self) -> dict:
        return {
            'X-TaskWarrior-UUID': self.item.uuid,
            'dtstart': self.item.planned_time,
            'duration': timedelta(minutes=self.item.duration_in_minutes),
            'summary': self.item.job['description']
        }

    def apply(self, calendar: caldav.Calendar):
        calendar.save_todo(no_overwrite=True, **self.todo_args)

    def __str__(self):
        return f'<{self.item.job["description"]} at {self.item.planned_time}>'

class DeleteStep:
    def __init__(self, item: ScheduleItem):
        pass

    def apply(self):
        print('Applying {self}...')

    def __str__(self):
        return '...'

class TodoSynchronizer:
    def __init__(self, new_schedule: list[ScheduleItem], calendar: caldav.Calendar):
        self.calendar = calendar
        self.new_items = new_schedule

    def plan(self) -> TodoSynchronizationPlan:
        current_items = self.calendar.todos(include_completed=True)
        taskwarrior_ids = {}
        steps = []
        seen = defaultdict(lambda: False)

        for item in current_items:
            print(item.icalendar_instance)
            taskwarrior_uuid = item.icalendar_instance.subcomponents[0].get('X-TaskWarrior-UUID')
            taskwarrior_ids[taskwarrior_uuid] = item
            item.delete()

        for item in self.new_items:
            if item.uuid not in taskwarrior_ids:
                steps.append(AddStep(item))
            else:
                seen[item.uuid] = True

        for uuid, has_been_seen in seen.items():
            if not has_been_seen:
                steps.append(DeleteStep(taskwarrior_ids[uuid]))

        return TodoSynchronizationPlan(steps)
