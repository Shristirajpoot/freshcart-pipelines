import pandas as pd
from sklearn.datasets import load_iris

# Import Mage's decorators only if they aren't already loaded
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


# data_loader marks this function as the pipeline's first step: it brings data in
@data_loader
def load_data(*args, **kwargs):
    iris = load_iris(as_frame=True)
    df = iris.frame                      # 4 feature columns + 'target'
    print('Rows loaded:', len(df))
    return df


# If the table doesn't have exactly 150 rows, the block fails and the pipeline stops
@test
def test_output(output, *args):
    assert len(output) == 150, 'Iris must have 150 rows'
