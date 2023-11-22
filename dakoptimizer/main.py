import os
import sys
import logging

logging.basicConfig(level=logging.INFO)

import dakota.environment as dakenv
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
import tools.maps


def main():
    main_inputs_dir = Path(os.environ["DY_SIDECAR_PATH_INPUTS"])
    main_outputs_dir = Path(os.environ["DY_SIDECAR_PATH_OUTPUTS"])

    caller_file_path = main_outputs_dir / "output_1" / "caller.json"
    map_file_path = main_inputs_dir / "input_2" / "map.json"

    map_object = tools.maps.oSparcFileMap(map_file_path, caller_file_path)

    def map_function(dak_inputs):
        param_sets = [dak_input["cv"] for dak_input in dak_inputs]
        obj_sets = map_object.evaluate(param_sets)

        dak_outputs = [{"fns": obj_set} for obj_set in obj_sets]
        logging.debug(f"Return objectives to dak: {dak_outputs}")
        return dak_outputs

    callbacks = {"map": map_function}

    opt_in_path = Path("opt.in")
    opt_in = opt_in_path.read_text()

    study = dakenv.study(callbacks=callbacks, input_string=opt_in)

    study.execute()


if __name__ == "__main__":
    main()
