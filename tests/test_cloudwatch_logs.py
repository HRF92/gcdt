# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
import time

from gcdt.cloudwatch_logs import delete_log_group, put_retention_policy, \
    describe_log_group, create_log_stream, put_log_events, create_log_group, \
    filter_log_events
from gcdt.ramuda_utils import check_and_format_logs_params

from gcdt_testtools import helpers
from gcdt_testtools.helpers_aws import awsclient  # fixture!

# Note: with this we do not want to test AWS cloudwatch
# we only want to make sure our wrappers for AWS calls work
# easiest to achieve this is to teset a whole log groug lifecycle


def test_log_group_lifecycle(awsclient):

    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)

    put_retention_policy(awsclient, fake_log_group_name, 545)

    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    my_log_event = {
        'timestamp': int(time.time()) * 1000,  # time in millis!!
        'message': 'meine oma fährt im hühnerstall motorrad'
    }
    put_log_events(awsclient, fake_log_group_name, fake_log_stream_name,
                   [my_log_event])

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info == {}


def test_set_retention_on_not_yet_existing_log_group(awsclient):
    fake_log_group_name = '/aws/lambda/%s' % helpers.random_string()

    put_retention_policy(awsclient, fake_log_group_name, 545)
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info == {}


def test_filter_log_events(awsclient):
    fake_log_group_name = '/aws/lambda/unittest_loggroup_%s' % helpers.random_string()
    fake_log_stream_name = 'unittest_logstream_%s' % helpers.random_string()

    create_log_group(awsclient, fake_log_group_name)
    create_log_stream(awsclient, fake_log_group_name, fake_log_stream_name)

    put_retention_policy(awsclient, fake_log_group_name, 545)

    info = describe_log_group(awsclient, fake_log_group_name)
    assert info['retentionInDays'] == 545
    assert info['storedBytes'] == 0

    now = helpers.time_now()
    log_event1 = {
        'timestamp': now - 300000,  # 5min
        'message': '1_meine oma fährt im hühnerstall motorrad'
    }
    log_event2 = {
        'timestamp': now - 120000,  # 2 min
        'message': '2_meine oma fährt im hühnerstall motorrad'
    }
    log_event3 = {
        'timestamp': now - 10000,   # 10 sec
        'message': '3_meine oma fährt im hühnerstall motorrad'
    }
    put_log_events(awsclient, fake_log_group_name, fake_log_stream_name,
                   [log_event1, log_event2, log_event3])

    # this testcase is potentially flaky since we depend on the log events
    # to eventually arrive in AWS cloudwatch
    time.sleep(10)  # automatically removed in playback mode!

    # filter log events
    logentries = filter_log_events(awsclient, fake_log_group_name,
                                   now - 180000, now - 60000)
    assert logentries == [log_event2]

    delete_log_group(awsclient, fake_log_group_name)
    # now we should not store anything anymore
    info = describe_log_group(awsclient, fake_log_group_name)
    assert info == {}