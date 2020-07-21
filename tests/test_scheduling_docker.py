import os
import pytest
import asyncio
import logging
from cpac.api.scheduling import Scheduler
from cpac.api.schedules import Schedule, DataSettingsSchedule, DataConfigSchedule, ParticipantPipelineSchedule
from cpac.api.backends.docker import DockerBackend, DockerParticipantPipelineSchedule
from cpac.api.backends.utils import consume

from conftest import Constants

try:
    from test_data.docker import build_image
except:
    pytest.skip("Skipping docker tests", allow_module_level=True)


@pytest.fixture
def docker_tag():
    build_image(tag='docker-test')
    return 'docker-test'


@pytest.fixture
def backend(docker_tag):
    return DockerBackend(tag=docker_tag)


@pytest.fixture
def scheduler(backend):
    return Scheduler(backend)


@pytest.mark.asyncio
async def test_scheduler_docker_settings(scheduler):

    async with scheduler as scheduler:
        schedule = scheduler.schedule(
            DataSettingsSchedule(
                data_settings=os.path.join(Constants.TESTS_DATA_PATH, 'data_settings_template.yml')
            )
        )

        await scheduler

        assert len(schedule['data_config']) == 4
        assert all(s['site'] == 'NYU' for s in schedule['data_config'])


@pytest.mark.asyncio
async def test_scheduler_docker_config(scheduler):

    async with scheduler as scheduler:
        schedule = scheduler.schedule(
            DataConfigSchedule(
                data_config='s3://fcp-indi/data/Projects/ABIDE/RawDataBIDS/NYU/',
                schedule_participants=False,
            )
        )

        await scheduler

        assert len(schedule['data_config']) == 4
        assert all(s['site'] == 'NYU' for s in schedule['data_config'])


@pytest.mark.asyncio
async def test_scheduler_docker_pipeline(scheduler):

    async with scheduler as scheduler:
        schedule = scheduler.schedule(
            ParticipantPipelineSchedule(
                subject=os.path.join(Constants.TESTS_DATA_PATH, 'data_config_template_single.yml')
            )
        )

        await scheduler

        logs = [log async for log in schedule.logs]

        assert len(logs) == 6
        for log_older, log_newer in zip(logs[:-1], logs[1:]):
            assert log_newer['finish'] > log_older['finish']


@pytest.mark.asyncio
async def test_scheduler_docker_pipeline_solo(backend):

    schedule = backend.specialize(
        ParticipantPipelineSchedule(
            subject=os.path.join(Constants.TESTS_DATA_PATH, 'data_config_template_single.yml')
        )
    )

    messages = [message async for message in schedule.run()]

    logs = [log async for log in schedule.logs]

    assert len(logs) == 6
    for log_older, log_newer in zip(logs[:-1], logs[1:]):
        assert log_newer['finish'] > log_older['finish']
