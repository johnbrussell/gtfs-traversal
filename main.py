def load_configuration():
    with open("configuration.json") as config_file:
        config = json.load(config_file)
    return config


if __name__ == "__main__":
    import json
    import gtfs_parsing.analyses.analyses as gtfs_analyses
    from gtfs_traversal import read_data

    analyses = gtfs_analyses.determine_analysis_parameters(load_configuration())
    analysis = analyses[0]

    data = read_data.read_data(analysis, "data")

    for element in data:
        print(len(element))
