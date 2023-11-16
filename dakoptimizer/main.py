import dakota.environment as dakenv
from pathlib import Path

opt_in_path = Path("opt.in")
opt_in = opt_in_path.read_text()

study = dakenv.study(callback=None, input_string=opt_in)

study.execute()
