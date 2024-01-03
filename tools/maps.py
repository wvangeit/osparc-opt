import time
import json
import logging
import socket

import osparc_control as oc

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ToolsMap")

POLLING_WAIT = 0.1  # second

from . import network


class oSparcFileMap:
    def __init__(self, map_file_path, caller_file_path):
        logger.info("Creating caller map")
        self.caller_file_path = caller_file_path
        self.map_file_path = map_file_path
        self.status = "connecting"
        self.map_transmitter = None

        poll_counter = 0
        while True:
            if self.map_file_path.exists():
                map_info = json.loads(self.map_file_path.read_text())
                if (
                    map_info["status"] == "connecting"
                    and self.status == "connecting"
                ):
                    payload = map_info["payload"]
                    map_host = payload["map_host"]
                    map_port = payload["map_port"]
                    self.start_map_transmitter(map_host, map_port)
                    self.status = "running"
                    break
                else:
                    raise ValueError(
                        f"Got wrong status from map at start: "
                        f"{map_info['status']}"
                    )

            time.sleep(POLLING_WAIT)
            poll_counter += 1

    def start_map_transmitter(self, remote_host, remote_port):
        tmp_sock = socket.socket()
        tmp_sock.bind(("", 0))
        listen_port = tmp_sock.getsockname()[1]
        tmp_sock.close()

        self.map_transmitter = self.start_transmitter(
            listen_port, remote_host, remote_port
        )

        self.connect_map(listen_port)

        logging.info(
            "Map caller set up transmitter to listen to port "
            f"{listen_port} for messages from {remote_host}:{remote_port}"
        )

    def connect_map(self, listen_port):
        command_dict = {
            "command": "connect",
            "payload": {
                "caller_host": network.get_osparc_hostname("optimizer"),
                "caller_port": listen_port,
            },
        }

        self.caller_file_path.write_text(json.dumps(command_dict, indent=4))

    def start_transmitter(self, listen_port, remote_host, remote_port):
        transmitter = oc.PairedTransmitter(
            remote_host=remote_host,
            exposed_commands=[],
            remote_port=remote_port,
            listen_port=listen_port,
        )

        transmitter.start_background_sync()

        return transmitter

    def evaluate(self, params_set):
        logger.info(f"Evaluating: {params_set}")

        payload = [
            (task_id, params) for task_id, params in enumerate(params_set)
        ]

        request_id = self.map_transmitter.request_with_delayed_reply(
            "map", params={"params_list": payload}
        )

        result_received = False
        while not result_received:
            result_received, objs_set = self.map_transmitter.check_for_reply(
                request_id=request_id
            )
            time.sleep(POLLING_WAIT)

        logger.info(f"Evaluation results: {objs_set}")

        return objs_set

    def map_function(self, *map_input):
        _ = map_input[0]
        params = map_input[1]

        return self.evaluate(params)

    def __del__(self):
        payload = {"command": "stop"}
        if self.map_transmitter is not None:
            self.map_transmitter.stop_background_sync()

        self.caller_file_path.write_text(json.dumps(payload, indent=4))

        self.status = "stopping"
