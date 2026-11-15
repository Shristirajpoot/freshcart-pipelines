# C4: my own block. Sits between load_iris and prepare_data.
if 'transformer' not in globals():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in globals():
    from mage_ai.data_preparation.decorators import test


# Passes the data through unchanged; the @test below is the actual quality gate
@transformer
def check_data(df, *args, **kwargs):
    print('Missing values:', int(df.isna().sum().sum()), '| classes:', df['target'].nunique())
    return df


# Fails (and stops the pipeline) if any value is missing or there are not exactly 3 classes
@test
def test_no_missing_and_3_classes(output, *args):
    assert output.isna().sum().sum() == 0, 'Data contains missing values'
    assert output['target'].nunique() == 3, 'Expected exactly 3 classes'
