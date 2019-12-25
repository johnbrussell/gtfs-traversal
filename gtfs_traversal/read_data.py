import os
import gtfs_parsing.analyses.analyses as gtfs_parser


def read_data(config, data_folder_name):
    data_location = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), data_folder_name)

    return gtfs_parser.parse(config, data_location)
