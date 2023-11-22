import os
import sys
import pathlib
import json
import time
import uuid
import logging
import socket

import osparc_control as oc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Map")

DEFAULT_POLLING_WAIT = 0.1  # seconds

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
import tools.network


def main():
    map = oSparcMap()

    map.start()


class oSparcMap:
    def __init__(self):
        """Constructor."""
        self.id = str(uuid.uuid4())

        # Input/output directories
        self.main_inputs_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_INPUTS"]
        )
        self.main_outputs_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_OUTPUTS"]
        )
        self.input_dirs = [
            self.main_inputs_dir / f"input_{i}" for i in range(3, 5)
        ]

        # Caller related
        self.caller_file_path = (
            self.main_inputs_dir / "input_2" / "caller.json"
        )
        self.caller_transmitter = None

        # Map related
        self.map_file_path = self.main_outputs_dir / "output_2" / "map.json"

        # Master related
        self.output_dir = self.main_outputs_dir / "output_1"
        self.master_file_path = self.output_dir / "master.json"

        # Engine related
        self.engine_ids = []
        self.engine_transmitters = {}
        self.engine_listen_ports = {}
        self.engine_request_ids = {}
        self.engine_submitted = {}

        # Task related
        self.torun_tasks = []
        self.running_tasks = []
        self.finished_tasks = []

        self.status = "connecting"

    def start(self, polling_wait=DEFAULT_POLLING_WAIT):
        logger.info("Starting mapping function")

        self.init_map_file()
        self.init_master_file()
        self.init_engine_files()
        polling_counter = 0

        while True:
            if self.status == "stopping":
                break

            if polling_counter % 20 == 0:
                logger.debug("Checking caller file ...")
            self.check_caller_file()

            if polling_counter % 20 == 0:
                logger.debug("Checking engine files ...")
            self.check_engine_files()

            if polling_counter % 20 == 0:
                logger.debug("Checking engine transmitters ...")
            self.check_engine_transmitters()

            if polling_counter % 20 == 0:
                logger.debug("Checking map transmitters ...")
            self.check_caller_transmitter()

            time.sleep(polling_wait)

            polling_counter += 1

        self.stop_engines()

    def check_caller_file(self):
        if self.caller_file_path.exists():
            content = json.loads(self.caller_file_path.read_text())
            command = content["command"]
            if command == "stop":
                self.status = "stopping"
            elif command == "connect":
                payload = content["payload"]
                if self.status == "connecting":
                    self.start_caller_transmitter(
                        payload["caller_host"], payload["caller_port"]
                    )
                    self.status == "ready"
            else:
                raise ValueError(f"Received unknown command: {command}")
        else:
            logger.debug(f"Caller file {self.caller_file_path} not found")

    def start_caller_transmitter(self, remote_host, remote_port):
        if self.caller_transmitter is not None:
            return

        self.map_manifest = oc.CommandManifest(
            action="map",
            description="evaluate parameter set and return objectives set",
            params=[
                oc.CommandParameter(
                    name="params_list", description="parameters list"
                ),
            ],
            command_type=oc.CommandType.WITH_DELAYED_REPLY,
        )

        self.caller_transmitter = self.start_transmitter(
            self.map_listen_port,
            remote_host,
            remote_port,
            manifests=[self.map_manifest],
        )

        logger.info(
            f"Started transmitter to talk at port {self.map_listen_port} with "
            f"a caller port at {remote_host}:{remote_port}"
        )

    def get_new_port(self):
        tmp_sock = socket.socket()
        tmp_sock.bind(("", 0))
        new_port = tmp_sock.getsockname()[1]
        tmp_sock.close()

        return new_port

    def start_engine_transmitter(self, engine_id, remote_host, remote_port):
        listen_port = self.get_new_port()

        transmitter = self.start_transmitter(
            listen_port, remote_host, remote_port
        )

        self.engine_transmitters[engine_id] = transmitter
        self.engine_listen_ports[engine_id] = listen_port
        logger.info(
            f"Started transmitter to talk at port {listen_port} with an "
            f"engine's port at {remote_host}:{remote_port}"
        )

    def start_transmitter(
        self, listen_port, remote_host, remote_port, manifests=[]
    ):
        transmitter = oc.PairedTransmitter(
            remote_host=remote_host,
            exposed_commands=manifests,
            remote_port=remote_port,
            listen_port=listen_port,
        )

        transmitter.start_background_sync()

        return transmitter

    def stop_engines(self):
        master_dict = self.read_master_dict()
        for engine_id in self.engine_ids:
            master_dict["engines"][engine_id] = {"task": {"command": "stop"}}

        self.write_master_dict(master_dict)

    def init_engine_files(self):
        for input_dir in self.input_dirs:
            engine_fn = input_dir / "engine.json"
            if engine_fn.exists():
                # Deleting engine file, if engine exists it will recreate it
                engine_fn.unlink()

    def populate_tasklist(self, map_input):
        self.torun_tasks = []
        self.running_tasks = []
        self.finished_tasks = []

        for task_id, param_values in map_input:
            params = {
                "gnabar_hh": param_values[0],
                "gkbar_hh": param_values[1],
            }
            task = {"command": "run", "task_id": task_id, "payload": params}
            self.torun_tasks.append(task)

        logger.info(f"Created tasks: {self.torun_tasks}")

    def send_map_output(self):
        objs = []

        self.finished_tasks.sort(key=lambda task: task["task_id"])
        for task in self.finished_tasks:
            obj = [
                task["result"]["step1.Spikecount"],
                task["result"]["step2.Spikecount"],
            ]
            objs.append(obj)

        self.caller_transmitter.reply_to_command(
            request_id=self.caller_request_id, payload=objs
        )
        self.caller_request_id = None

        self.finished_tasks = []

    def check_engine_transmitters(self):
        for engine_id, engine_transmitter in self.engine_transmitters.items():
            if (
                not self.engine_submitted[engine_id]
                and len(self.torun_tasks) != 0
            ):
                task = self.torun_tasks.pop()
                self.submit_task(task, engine_id)

            elif self.engine_submitted[engine_id]:
                self.receive_task(engine_id)

    def submit_task(self, task, engine_id):
        self.running_tasks.append(task)

        logger.debug(f"Submitting parameters: {task['payload']}")

        engine_transmitter = self.engine_transmitters[engine_id]

        request_id = engine_transmitter.request_with_delayed_reply(
            "eval",
            params={"params": task["payload"], "task_id": task["task_id"]},
        )
        self.engine_request_ids[engine_id] = request_id
        self.engine_submitted[engine_id] = True

    def receive_task(self, engine_id):
        request_id = self.engine_request_ids[engine_id]
        have_received, result = self.engine_transmitters[
            engine_id
        ].check_for_reply(request_id)
        if have_received:
            task_found = False
            for task in self.running_tasks:
                if task["task_id"] == result["task_id"]:
                    task["result"] = result["objs"]
                    self.running_tasks.remove(task)
                    self.finished_tasks.append(task)
                    self.engine_request_ids.pop(engine_id)
                    self.engine_submitted[engine_id] = False
                    logger.debug(f"Received result {task} from")
                    task_found = True
            assert task_found

    def check_caller_transmitter(self):
        if self.caller_transmitter is None:
            return

        for command in self.caller_transmitter.get_incoming_requests():
            logger.debug(f"Map received command: {command}")
            if command.action == self.map_manifest.action:
                params_list = command.params["params_list"]
                self.caller_request_id = command.request_id
                self.status = "computing"
                self.populate_tasklist(params_list)

        if (
            self.status == "computing"
            and len(self.torun_tasks) == 0
            and len(self.running_tasks) == 0
        ):
            self.send_map_output()
            self.status = "ready"

    def check_engine_files(self):
        for input_dir in self.input_dirs:
            engine_fn = input_dir / "engine.json"
            if engine_fn.exists():
                engine_info = self.get_engine_info(engine_fn)
                if engine_info["id"] not in self.engine_ids:
                    self.register_engine(engine_info)

    def process_engine_payload(self, engine_info):
        """Get payload from engine."""

        task_id = engine_info["task_id"]
        payload = engine_info["payload"]

        for task in self.running_tasks:
            if task["task_id"] == task_id:
                task["result"] = payload
                self.running_tasks.remove(task)
                self.finished_tasks.append(task)

        logger.debug(f"Received result {payload} from {engine_info['id']}")

    def connect_engine(self, engine_id):
        master_dict = self.read_master_dict()

        listen_port = self.engine_listen_ports[engine_id]
        master_dict["engines"][engine_id] = {
            "task": {
                "command": "connect",
                "payload": {
                    "master_host": tools.network.get_osparc_hostname("map"),
                    "master_port": listen_port,
                },
            }
        }

        self.write_master_dict(master_dict)

        self.engine_submitted[engine_id] = False

    def get_engine_info(self, engine_fn):
        engine_info = json.loads(engine_fn.read_text())

        return engine_info

    def register_engine(self, engine_info):
        """Register engines."""

        engine_id = engine_info["id"]
        engine_status = engine_info["status"]

        if engine_status == "connecting":
            self.engine_ids.append(engine_id)
            self.engine_submitted[engine_id] = False
            payload = engine_info["payload"]
            self.start_engine_transmitter(
                engine_id,
                remote_host=payload["engine_host"],
                remote_port=payload["engine_port"],
            )
            self.connect_engine(engine_id)
        else:
            raise ValueError(
                "Trying to register an engine that is not ready, "
                f"status: {engine_status}"
            )

        master_dict = self.read_master_dict()
        master_dict["engines"][engine_id] = {}
        # self.write_master_dict(master_dict)

        logger.info(f"Registered engine: {engine_id}")

    def init_map_file(self):
        self.map_listen_port = self.get_new_port()
        map_dict = {
            "status": "connecting",
            "payload": {
                "map_host": tools.network.get_osparc_hostname("map"),
                "map_port": self.map_listen_port,
            },
        }
        self.map_file_path.write_text(json.dumps(map_dict, indent=4))

    def init_master_file(self):
        master_dict = {"engines": {}, "id": self.id}
        self.write_master_dict(master_dict)

    def read_master_dict(self):
        master_dict = json.loads(self.master_file_path.read_text())

        return master_dict

    def write_master_dict(self, master_dict):
        self.master_file_path.write_text(json.dumps(master_dict, indent=4))

        logger.debug(f"Created new master.json: {master_dict}")


if __name__ == "__main__":
    main()
