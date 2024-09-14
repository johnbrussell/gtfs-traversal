class AnalysisDataMunger:  # Cannot be shared between Expanders
    def __init__(self, generalized_data_munger):
        self._data_munger = generalized_data_munger

    @classmethod
    def from_generalized_data_munger(cls, data_munger):
        return AnalysisDataMunger(data_munger)
