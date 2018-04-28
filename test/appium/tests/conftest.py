from _pytest.runner import runtestprotocol

from support.test_rerun import should_rerun_test
from tests import test_suite_data, debug
import requests
import re
import pytest
from datetime import datetime
from os import environ
from io import BytesIO
from sauceclient import SauceClient
from support.github_report import GithubHtmlReport
from support.testrail_report import TestrailReport

sauce_username = environ.get('SAUCE_USERNAME')
sauce_access_key = environ.get('SAUCE_ACCESS_KEY')
github_token = environ.get('GIT_HUB_TOKEN')

sauce = SauceClient(sauce_username, sauce_access_key)
github_report = GithubHtmlReport(sauce_username, sauce_access_key)
testrail_report = TestrailReport(sauce_username, sauce_access_key)


def pytest_addoption(parser):
    parser.addoption("--build",
                     action="store",
                     default=datetime.now().strftime('%Y-%m-%d-%H-%M'),
                     help="Specify build name")
    parser.addoption('--apk',
                     action='store',
                     default=None,
                     help='Url or local path to apk')
    parser.addoption('--env',
                     action='store',
                     default='sauce',
                     help='Specify environment: local/sauce')
    parser.addoption('--log',
                     action='store',
                     default=False,
                     help='Display each test step in terminal as plain text: True/False')
    parser.addoption('--pr_number',
                     action='store',
                     default=None,
                     help='Pull Request number')
    parser.addoption('--nightly',
                     action='store',
                     default=False,
                     help='boolean; For running extended test suite against nightly build')
    parser.addoption('--rerun_count',
                     action='store',
                     default=0,
                     help='How many times tests should be re-run if failed')


def get_rerun_count():
    return int(pytest.config.getoption('rerun_count'))


def is_master(config):
    return not hasattr(config, 'slaveinput')


def is_uploaded():
    stored_files = sauce.storage.get_stored_files()
    for i in range(len(stored_files['files'])):
        if stored_files['files'][i]['name'] == test_suite_data.apk_name:
            return True


def pytest_configure(config):
    if config.getoption('log'):
        import logging
        logging.basicConfig(level=logging.INFO)
    test_suite_data.apk_name = ([i for i in [i for i in config.getoption('apk').split('/')
                                             if '.apk' in i]])[0]
    if is_master(config):
        if config.getoption('nightly'):
            testrail_report.add_run(test_suite_data.apk_name)
        if config.getoption('env') == 'sauce':
            if not is_uploaded():
                if 'http' in config.getoption('apk'):
                    response = requests.get(config.getoption('apk'), stream=True)
                    response.raise_for_status()
                    file = BytesIO(response.content)
                    del response
                    requests.post('http://saucelabs.com/rest/v1/storage/'
                                  + sauce_username + '/' + test_suite_data.apk_name + '?overwrite=true',
                                  auth=(sauce_username, sauce_access_key),
                                  data=file,
                                  headers={'Content-Type': 'application/octet-stream'})
                else:
                    sauce.storage.upload_file(config.getoption('apk'))


def pytest_unconfigure(config):
    if is_master(config):
        if config.getoption('pr_number'):
            from github import Github
            repo = Github(github_token).get_user('status-im').get_repo('status-react')
            pull = repo.get_pull(int(config.getoption('pr_number')))
            pull.create_issue_comment(github_report.build_html_report())
        if config.getoption('nightly'):
            testrail_report.add_results()


@pytest.mark.hookwrapper
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == 'call':
        is_sauce_env = pytest.config.getoption('env') == 'sauce'
        current_test = test_suite_data.current_test
        if report.failed:
            current_test.testruns[-1].error = report.longreprtext
        if is_sauce_env:
            update_sauce_jobs(current_test.name, current_test.testruns[-1].jobs, report.passed)
        github_report.save_test(current_test)


def update_sauce_jobs(test_name, job_ids, passed):
    for job_id in job_ids:
        sauce.jobs.update_job(job_id, name=test_name, passed=passed)


def get_testrail_case_id(obj):
    if 'testrail_case_id' in obj.keywords._markers:
        return obj.keywords._markers['testrail_case_id'].args[0]


def pytest_runtest_setup(item):
    test_suite_data.set_current_test(item.name, testrail_case_id=get_testrail_case_id(item))
    test_suite_data.current_test.create_new_testrun()


def pytest_runtest_protocol(item, nextitem):
    for i in range(get_rerun_count()):
        reports = runtestprotocol(item, nextitem=nextitem)
        for report in reports:
            if report.failed and should_rerun_test(report.longreprtext):
                break  # rerun
        else:
            return True  # no need to rerun
