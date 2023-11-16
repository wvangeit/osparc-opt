import os
import json
import pathlib
import time
import uuid
import logging

import bluepyopt.ephys as ephys

DEFAULT_POLLING_WAIT = .1  # seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("evaluator")


def main():
    """Main"""

    engine = EvalEngine()
    engine.start()


class EvalEngine:
    def __init__(self, polling_wait=DEFAULT_POLLING_WAIT):
        """Constructor"""

        self.id = str(uuid.uuid4())
        self.output1_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_OUTPUTS"]
        ) / pathlib.Path("output_1")
        self.input2_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_INPUTS"]
        ) / pathlib.Path("input_2")
        self.master_file_path = self.input2_dir / "master.json"
        self.engine_file_path = self.output1_dir / "engine.json"
        self.status = "ready"
        self.polling_wait = polling_wait

    def start(self) -> None:
        """Start engine"""

        logger.info(f"Starting engine {self.id}")
        logger.info(f"Input 2 directory: {self.input2_dir}")
        logger.info(f"Output 1 directory: {self.output1_dir}")

        self.create_engine_file()

        self.watch_master_file()

    def create_engine_file(self) -> None:
        """Create engine file"""

        engine_dict = {"id": self.id, "status": self.status}

        with open(self.engine_file_path, "w") as engine_file:
            json.dump(engine_dict, engine_file, indent=2)

    def submit_result(self, task_id, result) -> None:
        """Create engine file"""

        engine_dict = {
            "id": self.id,
            "task_id": task_id,
            "status": "submitted",
            "payload": result,
        }

        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

    def read_master_dict(self) -> dict:
        with open(self.master_file_path) as master_file:
            master_dict = json.load(master_file)

        return master_dict

    def run_payload(self, payload):
        engine_dict = {
            "id": self.id,
            "status": self.status,
        }
        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

        return run_eval(payload)

    def watch_master_file(self) -> None:

        while True:
            logger.info(
                f"Engine {self.id}: Checking for master file at "
                f"{self.master_file_path}"
            )
            if self.master_file_path.exists():
                master_dict = self.read_master_dict()
                if self.id in master_dict["engines"]:
                    if "task" in master_dict["engines"][self.id]:
                        task_dict = master_dict["engines"][self.id]["task"]

                        if (
                            task_dict["command"] == "run"
                            and self.status == "ready"
                        ):
                            self.status = "busy"
                            logger.info(
                                f"Engine {self.id}: Received task:"
                                f" {task_dict}",
                            )
                            result = self.run_payload(task_dict["payload"])
                            logger.info(
                                f"Engine {self.id}: "
                                f"Calculated score: {result}",
                            )
                            self.submit_result(task_dict["task_id"], result)
                            self.status = "submitted"
                        elif task_dict["command"] == "get ready":
                            logger.info(
                                f"Engine {self.id}: Getting ready",
                            )
                            self.status = "ready"
                            self.create_engine_file()

                else:
                    logger.info(
                        f"Engine {self.id}: Didn't find any tasks for me"
                    )

            time.sleep(self.polling_wait)


def process_inputs(input_params_path, output_scores_path):
    """Process new inputs"""

    logger.info("Fetching input parameters:")
    with open(input_params_path, "r") as input_params_file:
        input_params = json.load(input_params_file)
    logger.info(f"Parameters found are: {input_params}")

    scores = run_eval(input_params)

    with open(output_scores_path, "w") as scores_file:
        json.dump(scores, scores_file)


def run_eval(input_params):
    logger.info("Starting simplecell")

    logging.debug("I am running in the directory: ", os.getcwd())

    logging.debug("Setting up simple cell model")

    morph = ephys.morphologies.NrnFileMorphology("simple.swc")

    somatic_loc = ephys.locations.NrnSeclistLocation(
        "somatic", seclist_name="somatic"
    )

    hh_mech = ephys.mechanisms.NrnMODMechanism(
        name="hh", suffix="hh", locations=[somatic_loc]
    )

    hh_mech = ephys.mechanisms.NrnMODMechanism(
        name="hh", suffix="hh", locations=[somatic_loc]
    )

    cm_param = ephys.parameters.NrnSectionParameter(
        name="cm",
        param_name="cm",
        value=1.0,
        locations=[somatic_loc],
        frozen=True,
    )

    gnabar_param = ephys.parameters.NrnSectionParameter(
        name="gnabar_hh",
        param_name="gnabar_hh",
        locations=[somatic_loc],
        bounds=[0.05, 0.125],
        frozen=False,
    )
    gkbar_param = ephys.parameters.NrnSectionParameter(
        name="gkbar_hh",
        param_name="gkbar_hh",
        bounds=[0.01, 0.075],
        locations=[somatic_loc],
        frozen=False,
    )

    simple_cell = ephys.models.CellModel(
        name="simple_cell",
        morph=morph,
        mechs=[hh_mech],
        params=[cm_param, gnabar_param, gkbar_param],
    )

    logging.debug("#############################")
    logging.debug("Simple neuron has been set up")
    logging.debug("#############################")

    logging.debug(simple_cell)

    logging.debug("Setting up stimulation protocols")
    soma_loc = ephys.locations.NrnSeclistCompLocation(
        name="soma", seclist_name="somatic", sec_index=0, comp_x=0.5
    )

    sweep_protocols = []

    for protocol_name, amplitude in [("step1", 0.01), ("step2", 0.05)]:
        stim = ephys.stimuli.NrnSquarePulse(
            step_amplitude=amplitude,
            step_delay=100,
            step_duration=50,
            location=soma_loc,
            total_duration=200,
        )
        rec = ephys.recordings.CompRecording(
            name="%s.soma.v" % protocol_name, location=soma_loc, variable="v"
        )
        protocol = ephys.protocols.SweepProtocol(protocol_name, [stim], [rec])
        sweep_protocols.append(protocol)
    twostep_protocol = ephys.protocols.SequenceProtocol(
        "twostep", protocols=sweep_protocols
    )

    logging.debug("#######################################")
    logging.debug("Stimulation protocols have been set up ")
    logging.debug("#######################################")

    logging.debug(twostep_protocol)

    logging.debug("Setting up objectives")
    efel_feature_means = {
        "step1": {"Spikecount": 1},
        "step2": {"Spikecount": 5},
    }

    objectives = []

    for protocol in sweep_protocols:
        stim_start = protocol.stimuli[0].step_delay
        stim_end = stim_start + protocol.stimuli[0].step_duration
        for efel_feature_name, mean in efel_feature_means[
            protocol.name
        ].items():
            feature_name = "%s.%s" % (protocol.name, efel_feature_name)
            feature = ephys.efeatures.eFELFeature(
                feature_name,
                efel_feature_name=efel_feature_name,
                recording_names={"": "%s.soma.v" % protocol.name},
                stim_start=stim_start,
                stim_end=stim_end,
                exp_mean=mean,
                exp_std=0.05 * mean,
            )
            objective = ephys.objectives.SingletonObjective(
                feature_name, feature
            )
            objectives.append(objective)

    logging.debug("############################")
    logging.debug("Objectives have been set up ")
    logging.debug("############################")

    logging.debug("Setting up fitness calculator")

    score_calc = ephys.objectivescalculators.ObjectivesCalculator(objectives)

    nrn = ephys.simulators.NrnSimulator()

    cell_evaluator = ephys.evaluators.CellEvaluator(
        cell_model=simple_cell,
        param_names=["gnabar_hh", "gkbar_hh"],
        fitness_protocols={twostep_protocol.name: twostep_protocol},
        fitness_calculator=score_calc,
        sim=nrn,
    )

    logging.debug("####################################")
    logging.debug("Fitness calculator have been set up ")
    logging.debug("####################################")

    logging.debug("Running test evaluation:")
    scores = cell_evaluator.evaluate_with_dicts(input_params)
    logging.info(f"Scores: {scores}")

    logging.debug("###############################")
    logging.debug("Test evaluation was successful ")
    logging.debug("###############################")

    return scores


if __name__ == "__main__":
    main()
