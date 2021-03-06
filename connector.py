import signal
import logging
import json
import time
import sys
import argparse

from stf_connect.client import SmartphoneTestingFarmClient, STFDevicesConnector, STFConnectedDevicesWatcher
from common import config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger('stf-connect')


def exit_gracefully(signum, frame):
    log.info("Stopping connect service...")
    try:
        thread_stop(devices_watcher_thread)
        thread_stop(devices_connector_thread)
    except NameError as e:
        log.warn("Poll thread is not defined, skipping... %s" % str(e))
    log.info("Stopping main thread...")
    stf.close_all()
    sys.exit(0)


def thread_stop(thread):
    thread.stop()
    thread.join()


def set_log_level():
    if args["log_level"]:
        log.info("Changed log level to {0}".format(args["log_level"].upper()))
        log.setLevel(args["log_level"].upper())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Utility for connecting '
                    'devices from STF'
    )
    parser.add_argument(
        '-groups', help='Device groups defined in spec file to connect'
    )
    parser.add_argument(
        "-log-level", help="Log level"
    )
    args = vars(parser.parse_args())
    signal.signal(signal.SIGINT, exit_gracefully)
    signal.signal(signal.SIGTERM, exit_gracefully)
    set_log_level()
    log.info("Starting connect service...")
    with open(config.get("main", "device_spec")) as f:
        device_spec = json.load(f)
    if args['groups']:
        log.info('Working only with specified groups: {0}'.format(args['groups']))
        specified_groups = args["groups"].split(",")
        device_spec = [device_group for device_group in device_spec if device_group.get("group_name") in specified_groups]
    stf = SmartphoneTestingFarmClient(
        host=config.get("main", "host"),
        common_api_path="/api/v1",
        oauth_token=config.get("main", "oauth_token"),
        device_spec=device_spec,
        devices_file_path="{0}/{1}".format(
            config.get("main", "devices_file_dir"),
            config.get("main", "devices_file_name")
        ),
        shutdown_emulator_on_disconnect=config.get("main", "shutdown_emulator_on_disconnect")
    )
    devices_connector_thread = STFDevicesConnector(stf)
    devices_watcher_thread = STFConnectedDevicesWatcher(stf)
    devices_watcher_thread.start()
    devices_connector_thread.start()

    while True:
        time.sleep(100)
