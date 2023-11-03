import os
import pathlib
import json
import time
import uuid
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("paramstest main")

DEFAULT_POLLING_WAIT = 1  # seconds


def main():

    param_creator = ParamCreator()

    param_creator.start()


class ParamCreator:

    def __init__(self):
        """Constructor"""
        self.id = str(uuid.uuid4())
        self.main_inputs_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_INPUTS"])
        self.main_outputs_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_OUTPUTS"])

        self.input_dirs = [
            self.main_inputs_dir
            / f'input_{i}' for i in range(
                3,
                5)]

        self.map_input_path = self.main_inputs_dir / 'input_2' / 'params.json'
        self.map_output_path = \
            self.main_outputs_dir / 'output_2' / 'objs.json'
        self.output_dir = self.main_outputs_dir / 'output_1'
        self.master_file_path = self.output_dir / 'master.json'
        self.engine_ids = []
        self.engine_submitted = {}
        self.status = 'ready'
        self.torun_tasks = []
        self.running_tasks = []
        self.finished_tasks = []

    def start(self, polling_wait=DEFAULT_POLLING_WAIT):
        logging.info("Starting mapping function")

        self.init_master_file()
        self.init_engine_files()
        polling_counter = 0
        while True:
            if polling_counter % 20 == 0:
                logging.info("Checking map file at "
                             f"{self.map_input_path.resolve()}")
            self.check_map_files()

            if polling_counter % 20 == 0:
                logging.info("Checking engine files ...")
            self.check_engine_files()

            time.sleep(polling_wait)

            polling_counter += 1

    def init_engine_files(self):

        for input_dir in self.input_dirs:
            engine_fn = input_dir / 'engine.json'
            if engine_fn.exists():
                # Deleting engine file, if engine exists it will recreate it
                engine_fn.unlink()

    def populate_tasklist(self):

        self.torun_tasks = []
        self.running_tasks = []
        self.finished_tasks = []

        with open(self.map_input_path) as map_input_file:
            map_input = json.load(map_input_file)
        self.map_input_path.unlink()

        for task_id, param_values in enumerate(map_input):
            params = {
                "gnabar_hh": param_values[0],
                "gkbar_hh": param_values[1]}
            task = {'command': 'run', 'task_id': task_id, 'payload': params}
            self.torun_tasks.append(task)

        logging.info(f"Created tasks: {self.torun_tasks}")

    def write_map_output(self):

        objs = []

        self.finished_tasks.sort(key=lambda task: task['task_id'])
        for task in self.finished_tasks:
            obj = [task['result']['step1.Spikecount'],
                   task['result']['step2.Spikecount']]
            objs.append(obj)

        with open(self.map_output_path, 'w') as map_output_file:
            json.dump(objs, map_output_file, indent=4)

        self.finished_tasks = []

    def check_map_files(self):

        if self.status == 'ready':
            if self.map_input_path.exists():
                self.populate_tasklist()
                self.status = 'computing'
        elif self.status == 'computing' and \
                len(self.torun_tasks) == 0 and \
                len(self.running_tasks) == 0:
            self.write_map_output()
            self.status = 'ready'

    def check_engine_files(self):

        for input_dir in self.input_dirs:
            engine_fn = input_dir / 'engine.json'
            if engine_fn.exists():
                engine_info = self.get_engine_info(engine_fn)
                if engine_info['id'] not in self.engine_ids:
                    self.register_engine(engine_info)

                if engine_info['status'] == 'ready' and \
                        not self.engine_submitted[engine_info['id']]:
                    if len(self.torun_tasks) != 0:
                        self.submit_task(engine_info)
                elif engine_info['status'] == 'submitted':
                    self.process_engine_payload(engine_info)
                    engine_fn.unlink()
                    self.set_engine_ready(engine_info['id'])

    def process_engine_payload(self, engine_info):
        """Get payload from engine"""

        task_id = engine_info['task_id']
        payload = engine_info['payload']

        for task in self.running_tasks:
            if task['task_id'] == task_id:
                task['result'] = payload
                self.finished_tasks.append(task)
                self.running_tasks.remove(task)

        logging.info(
            f'Received result {payload} '
            f'from {engine_info["id"]}')

    def set_engine_ready(self, engine_id):
        master_dict = self.read_master_dict()

        master_dict['engines'][engine_id] = {'task':
                                             {'command': 'get ready'}}

        self.write_master_dict(master_dict)

        self.engine_submitted[engine_id] = False

    def get_engine_info(self, engine_fn):
        with open(engine_fn) as engine_file:
            engine_info = json.load(engine_file)

        logging.info(f"Master received engine info: {engine_info}")
        return engine_info

    def register_engine(self, engine_info):
        """Register engines"""

        engine_id = engine_info['id']
        engine_status = engine_info['status']

        if engine_status == 'ready':
            self.engine_ids.append(engine_id)
            self.engine_submitted[engine_id] = False
        elif engine_status == 'submitted':
            self.engine_ids.append(engine_id)
            self.set_engine_ready(engine_info['id'])
        else:
            raise ValueError(
                "Trying to register an engine that is not ready, "
                f"status: {engine_status}")

        master_dict = self.read_master_dict()
        master_dict['engines'][engine_id] = {}
        self.write_master_dict(master_dict)

        logging.info(f"Registered engine: {engine_id}")

    def init_master_file(self):

        master_dict = {'engines': {}, 'id': self.id}
        self.write_master_dict(master_dict)

    def read_master_dict(self):
        with open(self.master_file_path) as master_file:
            master_dict = json.load(master_file)

        return master_dict

    def write_master_dict(self, master_dict):
        with open(self.master_file_path, 'w') as master_file:
            json.dump(master_dict, master_file, indent=4)

        logging.info("Created new master.json: {master_dict}")

    def submit_task(self, engine_dict):
        """Create dict with run info"""

        engine_id = engine_dict['id']

        task = self.torun_tasks.pop()
        self.running_tasks.append(task)

        master_dict = self.read_master_dict()

        engine_command_dict = master_dict['engines'][engine_id]

        if engine_dict['status'] != 'ready':
            raise ValueError("Trying to run on engine that is not ready")

        engine_command_dict['task'] = task

        self.write_master_dict(master_dict)

        self.engine_submitted[engine_id] = True
        logger.info(f"Sent task {task} to engine {engine_id}")


if __name__ == '__main__':
    main()
