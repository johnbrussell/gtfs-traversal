import json
import os

import pandas as pd

import gtfs_parsing.analyses.analyses as gtfs_parser


def load_configuration():
    with open("configuration.json") as config_file:
        config = json.load(config_file)
    return config


def read_data(config, data_folder_name):
    data_location = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), data_folder_name)

    return gtfs_parser.parse(config, data_location)

def read_stops(config, data_folder_name):
    data_location = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), data_folder_name)
    df = pd.read_csv(os.path.join(data_location, config.agency, 'data', config.date, 'stops.txt'))
    return df
