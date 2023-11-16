import time
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Tools")

POLLING_WAIT = .1  # second


class oSparcFileMap:
    def __init__(self, input_file_path, output_file_path):
        self.input_file_path = input_file_path
        self.output_file_path = output_file_path

    def evaluate(self, params):

        if self.output_file_path.exists():
            self.output_file_path.unlink()

        logger.debug(
            f"Writing params list {params} to {self.input_file_path.resolve()}"
        )

        self.input_file_path.write_text(json.dumps(params, indent=4))

        poll_counter = 0

        while True:
            if poll_counter % 20 == 0:
                logger.info(
                    "Waiting for objectives file: "
                    f"{self.output_file_path.resolve()}"
                )

            if self.output_file_path.exists():
                with open(self.output_file_path) as output_file:
                    objs = json.load(output_file)
                self.output_file_path.unlink(missing_ok=True)
                self.input_file_path.unlink(missing_ok=True)
                logging.debug(f"Filemap returning objectives {objs}")
                return objs
            else:
                time.sleep(POLLING_WAIT)
                poll_counter += 1

    def map_function(self, *map_input):
        _ = map_input[0]
        params = map_input[1]

        return self.evaluate(params)
