import os
import unittest.mock as mock
import sys
sys.path.append(".")
import json

import main

builtin_open = open


objs_path = 'tests/test-inputs/input_2/objs.json'
n_offspring = 3


def mock_open(*args, **kwargs):
    if str(args[0]) == objs_path:
        mock_data = [[0.1, 0.1] for _ in range(n_offspring)]
        return mock.mock_open(read_data=json.dumps(mock_data))(*args, **kwargs)
    return builtin_open(*args, **kwargs)


@mock.patch('pathlib.Path.exists')
@mock.patch('pathlib.Path.unlink')
@mock.patch("builtins.open", mock_open)
def test_main(mocked_exists, mocked_unlink):
    mocked_exists.return_value = True
    mocked_unlink.return_value = True
    os.environ['DY_SIDECAR_PATH_INPUTS'] = 'tests/test-inputs'
    os.environ['DY_SIDECAR_PATH_OUTPUTS'] = 'tests/test-outputs'
    final_pop = main.main()

    assert final_pop == [
        [0.11342977723255462, 0.02657948667306241],
        [0.11090795157113967, 0.02657948667306241],
        [0.11090795157113967, 0.037917330565569764],
        [0.1098333304539681, 0.02657948667306241],
        [0.11090795157113967, 0.02657948667306241],
        [0.11090795157113967, 0.024593577932680303]]
