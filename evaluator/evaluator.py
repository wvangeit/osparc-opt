import os
import sys
import json
import pathlib
import time
import uuid
import logging
import osparc_control as oc
import socket

sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))
import tools.network

import bluepyopt.ephys as ephys

DEFAULT_POLLING_WAIT = 0.1  # seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Evaluator")


def main(name):
    """Main."""

    engine = EvalEngine(name)
    engine.start()


class EvalEngine:
    def __init__(self, name, polling_wait=DEFAULT_POLLING_WAIT):
        """Constructor."""

        self.name = name
        self.id = str(uuid.uuid4())
        self.output1_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_OUTPUTS"]
        ) / pathlib.Path("output_1")
        self.input2_dir = pathlib.Path(
            os.environ["DY_SIDECAR_PATH_INPUTS"]
        ) / pathlib.Path("input_2")
        self.master_file_path = self.input2_dir / "master.json"
        self.engine_file_path = self.output1_dir / "engine.json"
        self.status = "connecting"
        self.polling_wait = polling_wait
        self.transmitter = None

    def start(self) -> None:
        """Start engine."""

        self.create_engine_file()

        while True:
            if self.status == "stopping":
                break

            self.check_master_file()
            self.check_transmitter()

            time.sleep(self.polling_wait)

        self.stop_transmitter()

    def stop_transmitter(self):
        if self.transmitter is not None:
            self.transmitter.stop_background_sync()
            self.transmitter = None

    def create_transmitter(self, remote_host, remote_port):
        self.eval_manifest = oc.CommandManifest(
            action="eval",
            description="evaluate parameters and return objectives",
            params=[
                oc.CommandParameter(name="task_id", description="task_id"),
                oc.CommandParameter(name="params", description="parameters"),
            ],
            command_type=oc.CommandType.WITH_DELAYED_REPLY,
        )

        self.transmitter = oc.PairedTransmitter(
            remote_host=remote_host,
            exposed_commands=[self.eval_manifest],
            remote_port=remote_port,
            listen_port=int(self.listen_port),
        )

    def start_transmitter(self, remote_host, remote_port):
        self.create_transmitter(remote_host, remote_port)

        self.transmitter.start_background_sync()

        logger.info(
            f"Started engine {self.id} listening at port {self.listen_port} "
            f"for input from {remote_host}:{remote_port}"
        )

        self.status = "ready"
        self.submit_status()

    def check_transmitter(self):
        if self.transmitter is None:
            return

        for command in self.transmitter.get_incoming_requests():
            logger.debug(f"Engine {self.id} received command: {command}")
            if command.action == self.eval_manifest.action:
                params = command.params["params"]
                task_id = command.params["task_id"]
                objs = run_eval(params)
                self.transmitter.reply_to_command(
                    request_id=command.request_id,
                    payload={"task_id": task_id, "objs": objs},
                )

    def create_engine_file(self) -> None:
        """Create engine file."""

        tmp_sock = socket.socket()
        tmp_sock.bind(("", 0))
        self.listen_port = tmp_sock.getsockname()[1]
        tmp_sock.close()

        engine_dict = {
            "id": self.id,
            "status": "connecting",
            "payload": {
                "engine_host": tools.network.get_osparc_hostname(self.name),
                "engine_port": self.listen_port,
            },
        }

        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

    def submit_result(self, task_id, result) -> None:
        """Create engine file."""

        engine_dict = {
            "id": self.id,
            "task_id": task_id,
            "status": "submitted",
            "payload": result,
        }

        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

    def submit_status(self) -> None:
        """Create engine file."""

        engine_dict = {
            "id": self.id,
            "status": self.status,
        }

        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

    def read_master_dict(self) -> dict:
        master_dict = json.loads(self.master_file_path.read_text())

        return master_dict

    def run_payload(self, payload):
        engine_dict = {
            "id": self.id,
            "status": self.status,
        }
        self.engine_file_path.write_text(json.dumps(engine_dict, indent=2))

        return run_eval(payload)

    def check_master_file(self) -> None:
        logger.debug(
            f"Engine {self.id}: Checking for master file at "
            f"{self.master_file_path}"
        )

        if self.master_file_path.exists():
            master_dict = self.read_master_dict()
            if self.id in master_dict["engines"]:
                if "task" in master_dict["engines"][self.id]:
                    task_dict = master_dict["engines"][self.id]["task"]
                    command = task_dict["command"]
                    if command == "stop":
                        self.status = "stopping"
                    elif command == "connect":
                        if self.status == "connecting":
                            payload = task_dict["payload"]

                            self.start_transmitter(
                                payload["master_host"], payload["master_port"]
                            )
                    else:
                        raise ValueError(
                            f"Received unknown command: {command}"
                        )


def run_eval(input_params):

    logger.info(f"Running evaluation of {input_params}")
    logger.debug("Starting simplecell")

    logger.debug("I am running in the directory: ", os.getcwd())

    logger.debug("Setting up simple cell model")

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

    logger.debug("#############################")
    logger.debug("Simple neuron has been set up")
    logger.debug("#############################")

    logger.debug(simple_cell)

    logger.debug("Setting up stimulation protocols")
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

    logger.debug("#######################################")
    logger.debug("Stimulation protocols have been set up ")
    logger.debug("#######################################")

    logger.debug(twostep_protocol)

    logger.debug("Setting up objectives")
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

    logger.debug("############################")
    logger.debug("Objectives have been set up ")
    logger.debug("############################")

    logger.debug("Setting up fitness calculator")

    score_calc = ephys.objectivescalculators.ObjectivesCalculator(objectives)

    nrn = ephys.simulators.NrnSimulator()

    cell_evaluator = ephys.evaluators.CellEvaluator(
        cell_model=simple_cell,
        param_names=["gnabar_hh", "gkbar_hh"],
        fitness_protocols={twostep_protocol.name: twostep_protocol},
        fitness_calculator=score_calc,
        sim=nrn,
    )

    logger.debug("####################################")
    logger.debug("Fitness calculator have been set up ")
    logger.debug("####################################")

    logger.debug("Running test evaluation:")
    scores = cell_evaluator.evaluate_with_dicts(input_params)
    logger.debug(f"Scores: {scores}")

    logger.debug("###############################")
    logger.debug("Test evaluation was successful ")
    logger.debug("###############################")

    return scores


if __name__ == "__main__":
    main()
