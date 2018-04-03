from threading import Thread
from functools import singledispatch

from celery import Celery
from celery.schedules import crontab
from celery.bin.purge import purge

from nudgebot.settings import CurrentProject
from nudgebot.base import Singleton


class CeleryRunner(Thread, metaclass=Singleton):
    """
    The celery runner object.

    Running the celery task manager in a separated thread.
    """
    celery = Celery()

    @celery.task
    def run_periodic_task(self, task_class_name):
        """Running a periodic task"""
        task = next(task for task in CurrentProject().TASKS if task.__name__ == task_class_name)
        task().handle()

    def setup_periodic_tasks(self, sender, **kwargs):
        """Setup the periodic tasks"""
        from nudgebot.tasks.base import PeriodicTask
        for task_class in CurrentProject().TASKS:
            if issubclass(task_class, PeriodicTask):
                print(f'Adding periodic task to celery: {task_class}')
                assert isinstance(task_class.CRONTAB, crontab), \
                    ('CRONTAB static attribute should be deifned in periodic '
                     f'task and must be an instance of {crontab}')
                sender.add_periodic_task(
                    task_class.CRONTAB,
                    self.run_periodic_task.s(task_class.__name__)
                )

    @singledispatch
    def run(self):
        """Running the celery app"""
        purge(self.celery)
        self.celery.on_after_configure.connect(self.setup_periodic_tasks)
        self.celery.worker_main(['--loglevel=info', '--beat'])
