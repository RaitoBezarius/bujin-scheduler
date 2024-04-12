import click
import caldav
import keyring
import taskw
from zoneinfo import ZoneInfo
from datetime import datetime

from bujin_scheduler.synchronizer import TodoSynchronizer
from .scheduler import SchedulerV1, SchedulerConfiguration, SchedulingPlan
from .secrets import url, username, password

from typing import Tuple, Type
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict, TomlConfigSettingsSource, PydanticBaseSettingsSource

class SchedulingConfiguration(BaseModel):
    target_calendar: str
    timezone: str
    # 14 days
    planning_horizon_in_days: int = 14

class ConstraintConfiguration(BaseModel):
    # Mon - Fri
    workweek: Tuple[int, int] = (0, 5)
    # Sat - Sun
    weekend: Tuple[int, int] = (5, 7)

    # 9 to 5.
    operation_range: Tuple[int, int] = (9, 17)

    # 5 big tasks
    ideal_energy_level: int = 5
    # No constraint by default
    calendars: list[str] = []

class SolverConfiguration(BaseModel):
    # Tasks of 1 hour
    discretization_in_minutes: int = 60

class AppConfig(BaseSettings):
    scheduling: SchedulingConfiguration
    constraints: ConstraintConfiguration
    solver: SolverConfiguration


    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (TomlConfigSettingsSource(settings_cls),)

    def get_scheduler_config(self) -> SchedulerConfiguration:
        today = datetime.now(ZoneInfo(self.scheduling.timezone))
        start = today.replace(day=today.day + 1, hour=self.constraints.operation_range[0], minute=0, second=0, microsecond=0)

        return SchedulerConfiguration(
            ideal_energy_level_per_day=self.constraints.ideal_energy_level,
            planning_horizon=self.scheduling.planning_horizon_in_days,
            discretization_per_day=self.solver.discretization_in_minutes,
            planning_range_per_day=(start, self.constraints.operation_range[1])
        )

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


def compute_plan(config: AppConfig) -> SchedulingPlan:
    click.echo('Generating a plan...')

    tasks = taskw.TaskWarrior(marshal=True)

    scheduler_configuration = config.get_scheduler_config()
    scheduler = SchedulerV1(
        scheduler_configuration,
        find_calendar(config.scheduling.target_calendar),
        tasks
    )
    return scheduler.plan()



@click.group()
@click.option('--scheduler-config-file', default=f'{click.get_app_dir("bujin-scheduler")}.toml')
@click.pass_context
def cli(ctx, scheduler_config_file):
    ctx.ensure_object(dict)

    AppConfig.model_config = SettingsConfigDict(toml_file=scheduler_config_file)
    ctx.obj['app_config'] = AppConfig()

@cli.command()
@click.pass_context
def plan(ctx):
    config: AppConfig = ctx.obj['app_config']
    print(config)
    plan = compute_plan(config)
    synchronizer = TodoSynchronizer(plan.planning, find_calendar(config.scheduling.target_calendar))
    synchronizer.plan().diagnose()

@cli.command()
@click.pass_context
def apply(ctx):
    config: AppConfig = ctx.obj['app_config']
    target_calendar = find_calendar(config.scheduling.target_calendar)
    plan = compute_plan(config)
    synchronizer = TodoSynchronizer(plan.planning, target_calendar)
    synchronizer.plan().apply(target_calendar)


if __name__ == '__main__':
    cli()
