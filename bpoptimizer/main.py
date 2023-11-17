import os
import sys

from pathlib import Path

import bluepyopt as bpopt

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Optimizer")

sys.path.append(str(Path(__file__).resolve().parent.parent))
import tools.maps

POLLING_WAIT = 0.1  # second


def main():
    """Main"""

    main_inputs_dir = Path(os.environ["DY_SIDECAR_PATH_INPUTS"])
    main_outputs_dir = Path(os.environ["DY_SIDECAR_PATH_OUTPUTS"])

    objs_file_path = main_inputs_dir / "input_2" / "objs.json"
    params_file_path = main_outputs_dir / "output_1" / "params.json"

    map_object = tools.maps.oSparcFileMap(params_file_path, objs_file_path)
    map_function = map_object.map_function

    optimizer = Optimizer(map=map_function)
    final_pop = optimizer.start()

    return final_pop


class DummyEvaluator(bpopt.evaluators.Evaluator):
    """
    This evaluator is only made to pass to bpopt, evaluations are
    intercepted by the map
    """

    def init_simulator_and_evaluate_with_lists(
        self, param_list=None, target="scores"
    ):
        return self.evaluate_with_lists(param_list=param_list, target=target)

    def evaluate_with_lists(self, param_list=None, target="scores"):
        """Run evaluation with lists as input and outputs"""

        print(f"Evaluating with lists: {param_list}")

        return [1.0, 1.0]


class Optimizer:
    def __init__(self, map):
        self.params = [
            bpopt.parameters.Parameter("gnabar_hh", bounds=[0.05, 0.125]),
            bpopt.parameters.Parameter("gkbar_hh", bounds=[0.01, 0.075]),
        ]
        self.objectives = [
            bpopt.objectives.Objective(f"obj{i}") for i in range(2)
        ]

        self.evaluator = DummyEvaluator(
            params=self.params, objectives=self.objectives
        )

        self.map = map

    def start(self):
        logger.info("Starting optimization")

        optimisation = bpopt.optimisations.DEAPOptimisation(
            evaluator=self.evaluator, offspring_size=3, map_function=self.map
        )

        final_pop, hall_of_fame, logs, hist = optimisation.run(max_ngen=10)
        logger.info(f"Optimization done: {final_pop}")

        return final_pop


if __name__ == "__main__":
    main()
