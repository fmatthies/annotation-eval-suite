import pathlib
import importlib
bc = importlib.import_module("base_config")

lines = pathlib.Path("../config").read_text().split("\n")
bc.setup_config(config_str=lines[0].split("=")[1], slayer_str=lines[1].split("=")[1])

db_construction = bc.db_construction
database_info = bc.database_info
layers = bc.layers
DefaultTableNames = bc.DefaultTableNames
