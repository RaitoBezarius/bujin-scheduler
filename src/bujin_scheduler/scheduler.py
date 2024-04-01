import caldav
import taskw
from dataclasses import dataclass
import click
from collections import defaultdict
import cpmpy as cp
from typing import Any, Tuple
from datetime import timedelta, datetime

@dataclass
class SchedulerConfiguration:
    ideal_energy_level_per_day: int
    # How far should we schedule in days?
    planning_horizon: int
    # How long are discrete time unit in the day for scheduling, in minutes?
    # e.g. 60 minutes for 1 hour slot per day.
    discretization_per_day: int
    # Day start / day end range.
    planning_range_per_day: Tuple[int, int]

@dataclass
class ScheduleItem:
    job: Any
    planned_time: datetime
    duration_in_minutes: int

    @property
    def uuid(self) -> str:
        return self.job['uuid']

class SchedulingPlan:
    def __init__(self):
        self.transport_matrix = None
        self.planning: list[ScheduleItem] = []

    @classmethod
    def from_solution(cls, transport_matrix, config: SchedulerConfiguration, jobs: list, n_days: int, n_slots: int) -> 'SchedulingPlan':
        plan = cls()
        plan.transport_matrix = transport_matrix
        n_jobs = len(jobs)
        # TODO: make next start configurable.
        start = datetime.now().replace(day=datetime.now().day + 1, hour=config.planning_range_per_day[0], minute=0, second=0, microsecond=0) # start at planning_range_per_day[0]
        planning = []
        values = transport_matrix.value()
        for day in range(n_days):
            for slot in range(n_slots):
                max_ = sum(values[(job, day, s)] for s in range(slot + 1) for job in range(len(jobs)))
                assert max_ <= slot + 1

        for job in range(n_jobs):
            for day in range(n_days):
                for slot in range(n_slots):
                    if values[(job, day, slot)] == 1:
                        planned_time = start + timedelta(days=day, minutes=config.discretization_per_day*slot)
                        planning.append(ScheduleItem(
                            job=jobs[job],
                            planned_time=planned_time,
                            duration_in_minutes=config.discretization_per_day
                        ))
        plan.planning = planning
        reverse_indexes = {job['description']: job_index for (job_index, job) in enumerate(jobs)}
        for item in sorted(planning, key=lambda item: item.planned_time):
            print(item.job['description'], item.planned_time, reverse_indexes[item.job['description']])
        return plan

class SchedulerV1:
    def __init__(self, scheduling_configuration: SchedulerConfiguration, target_calendar: caldav.Calendar, tasks: taskw.TaskWarrior):
        self.scheduling_calendar = target_calendar
        self.tasks = tasks
        self.configuration = scheduling_configuration

    @property
    def n_slots(self) -> int:
        return (self.configuration.planning_range_per_day[1] - self.configuration.planning_range_per_day[0].hour + 1)

    @property
    def n_days(self) -> int:
        return self.configuration.planning_horizon

    @property
    def max_jobs(self) -> int:
        return self.n_slots * self.n_days

    def evaluate_weight(self, job) -> int:
        age_factor = 1.2

        # TODO: take into account deadlines.
        return (age_factor ** job.get('age', 0)) + job.get('urgency', 0)

    def evaluate_energy(self, job) -> int:
        # TODO: make it dependent upon the job.
        return 1

    def build_model(self, jobs: list) -> cp.Model:
        """
        Prepare a model to solve which will yield >= 0 solutions
        to the scheduling problem.
        """
        assert len(jobs) <= self.max_jobs, f"Unsatisfiable model, more jobs ({len(jobs)}) than possible scheduling slots ({self.max_jobs})!"
        # Compute all the weights for jobs.
        weights = defaultdict(lambda: 0) # by default, we ignore.
        energy = defaultdict(lambda: 0) # by default, we ignore.
        for j, job in enumerate(jobs):
            weights[j] = self.evaluate_weight(job)
        model = cp.Model()
        # jobs x day x discretization slot in the day
        x_jdt = cp.intvar(0, 1, shape=(len(jobs), self.n_days, self.n_slots), name="x_jtd")
        # C1: sum_(d=0)^(l - 1) sum_(t=0)^(l_d - 1) x_jdt = 1 for all j=1..n_jobs
        # job is processed once.
        for j in range(len(jobs)):
            C_j = cp.sum([cp.sum([x_jdt[(j, d, t)] for t in range(self.n_slots)]) for d in range(self.n_days)]) == 1
            print(C_j)
            model += C_j
        # C2: sum_(j=1)^n sum_(s=0)^(t - 1) x_jds <= t for all t = 0..l_d for all d = 0..l
        # processing is serial, not parallel, there cannot be more than t jobs processed in the window [[0, t[[ for any day for any t.
        for d in range(self.n_days):
            for t in range(self.n_slots):
                model += cp.sum(
                    [cp.sum(
                        [x_jdt[(j, d, s)] for s in range(t + 1)]
                    ) for j in range(len(jobs))]
                ) <= t + 1
        # we want to minimize sum_j sum_d sum_t w_j (t + e_j) x_jdt
        model.minimize(cp.sum(
            [cp.sum(
                [cp.sum(
                    [weights[j] * (t + energy[j]) * x_jdt[(j, d, t)]
                     for t in range(self.n_slots)]
                ) for d in range(self.n_days)]
            ) for j in range(len(jobs))]
        ))
        # that is, the energy expense over the planning horizon.
        # remaining constraints:
        # TODO: - take elements from the availabilities calendar and force x_jtd = 0 for periods where unavailable.
        # TODO: - take the energy gauge availability.
        return model, x_jdt

    def plan(self) -> SchedulingPlan:
        """
        Prepare a plan to update the current scheduling situation.
        """
        # The idea here is to build a model and throw it to a solver.
        pending_tasks = self.tasks.load_tasks().get('pending', [])
        if not pending_tasks:
            click.echo('No pending task, no schedule to plan!')
            return SchedulingPlan()

        # TODO: can we consider the full range of tasks without combinatorial explosion?
        model, time_variables = self.build_model(pending_tasks[:self.max_jobs])
        print(f'Model has {len(model.constraints)} constraints')
        print(model)
        has_solution = model.solve()
        print("Status: ", model.status())
        if has_solution:
            print(model.objective_value())
            return SchedulingPlan.from_solution(time_variables, self.configuration, pending_tasks[:self.max_jobs], self.n_days, self.n_slots)
        else:
            raise RuntimeError('Failed to solve the problem? UNSAT?')

