import pathlib
import importlib
import configparser
bc = importlib.import_module(".base_config", package="app_constants")

this_path = pathlib.Path(__file__).parent
config_ini = configparser.ConfigParser()
config_ini.read(pathlib.Path(this_path / ".." / "config.ini").resolve())
bc.setup_config(config_str=config_ini["DEFAULT"]["name"], slayer_str=config_ini["DEFAULT"]["sentence_layer"])

db_construction = bc.db_construction
database_info = bc.database_info
layers = bc.layers
DefaultTableNames = bc.DefaultTableNames
