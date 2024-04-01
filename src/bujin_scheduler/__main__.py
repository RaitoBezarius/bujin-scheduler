import click
import caldav
import keyring
import taskw
from zoneinfo import ZoneInfo
from datetime import datetime

from bujin_scheduler.synchronizer import TodoSynchronizer
from .scheduler import SchedulerV1, SchedulerConfiguration, SchedulingPlan
from .secrets import url, username, password

def find_calendar(calendar_id: str) -> caldav.Calendar:
    with caldav.DAVClient(url=url, username=username, password=password) as client:
        me = client.principal()
        calendars = me.calendars()
        target_calendar = None
        for calendar in calendars:
            if calendar.id == calendar_id:
                target_calendar = calendar

        if not target_calendar:
            raise RuntimeError(f"Calendar '{calendar_id}' not found!")

        return target_calendar


def compute_plan(calendar_id: str, constraint_calendar_ids: list[str]) -> SchedulingPlan:
    click.echo('Generating a plan...')

    today = datetime.now(ZoneInfo("Europe/Paris"))
    start = today.replace(day=today.day + 1, hour=10, minute=0, second=0, microsecond=0)

    tasks = taskw.TaskWarrior(marshal=True)
    scheduler = SchedulerV1(
        SchedulerConfiguration(ideal_energy_level_per_day=100, planning_horizon=3, discretization_per_day=60, planning_range_per_day=(start, 16)),
        find_calendar(calendar_id),
        tasks
    )
    return scheduler.plan()



@click.group()
def cli():
    pass

@cli.command()
@click.option('--calendar-id', prompt='Your calendar ID?', help='Calendar ID for the scheduling calendar')
@click.option('--constraint-calendar-id', help='Constraint calendar IDs for forbidden zone', default=[])
def plan(calendar_id: str, constraint_calendar_id: list[str]):
    plan = compute_plan(calendar_id, constraint_calendar_id)
    synchronizer = TodoSynchronizer(plan.planning, find_calendar(calendar_id))
    synchronizer.plan().diagnose()

@cli.command()
@click.option('--calendar-id', prompt='Your calendar ID?', help='Calendar ID for the scheduling calendar')
@click.option('--constraint-calendar-id', help='Constraint calendar IDs for forbidden zone', default=[])
def apply(calendar_id: str, constraint_calendar_id: list[str]):
    target_calendar = find_calendar(calendar_id)
    plan = compute_plan(calendar_id, constraint_calendar_id)
    synchronizer = TodoSynchronizer(plan.planning, target_calendar)
    synchronizer.plan().apply(target_calendar)


if __name__ == '__main__':
    cli()
