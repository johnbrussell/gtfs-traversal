def load_configuration():
    with open("configuration.json") as config_file:
        config = json.load(config_file)
    return config


if __name__ == "__main__":
    import json
    import os
    import gtfs_parsing.analyses.analyses as gtfs_analyses

    analyses = gtfs_analyses.determine_analysis_parameters(load_configuration())

    data_location = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

    analysis = analyses[0]

    data = gtfs_analyses.parse(analysis, data_location)
