import time
import json
import uuid
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("ToolsMap")

POLLING_WAIT = 1  # second


class oSparcFileMap:
    def __init__(self, map_file_path, caller_file_path):
        logger.info("Creating caller map")
        self.caller_file_path = caller_file_path
        self.map_file_path = map_file_path

    def create_map_input_payload(self, tasks_uuid, params_sets):
        payload = {}
        payload["uuid"] = tasks_uuid
        payload["command"] = "run"
        payload["tasks"] = []

        for param_set in params_sets:
            task = {}
            task_input = task["input"] = {}
            task_output = task["output"] = {}

            task_input["InputFile1"] = {
                "type": "FileJSON",
                "filename": "input.json",
                "value": param_set,
            }
            task_output["OutputFile1"] = {
                "type": "FileJSON",
                "filename": "output.json",
            }

            payload["tasks"].append(task)

        return payload

    def read_map_output_payload(self, task_uuid, map_output_payload):
        return map_output_payload

    def evaluate(self, params_set):
        logger.info(f"Evaluating: {params_set}")

        tasks_uuid = str(uuid.uuid4())
        map_input_payload = self.create_map_input_payload(
            tasks_uuid, params_set
        )

        self.caller_file_path.write_text(
            json.dumps(map_input_payload, indent=4)
        )

        waiter = 0
        payload_uuid = ""
        while not self.map_file_path.exists() or payload_uuid != tasks_uuid:
            if self.map_file_path.exists():
                payload_uuid = json.loads(self.map_file_path.read_text())[
                    "uuid"
                ]
                if waiter % 10 == 0:
                    logger.info(
                        f"Waiting for tasks uuid to match: payload:{payload_uuid} tasks:{tasks_uuid}"
                    )
            else:
                if waiter % 10 == 0:
                    logger.info(
                        f"Waiting for map results at: {self.map_file_path.resolve()}"
                    )
            time.sleep(POLLING_WAIT)
            waiter += 1

        map_output_payload = json.loads(self.map_file_path.read_text())

        objs_set = self.read_map_output_payload(map_output_payload)

        logger.info(f"Evaluation results: {objs_set}")

        return objs_set

    def map_function(self, *map_input):
        _ = map_input[0]
        params = map_input[1]

        return self.evaluate(params)

    def __del__(self):
        payload = {"command": "stop"}

        self.caller_file_path.write_text(json.dumps(payload, indent=4))

        self.status = "stopping"
