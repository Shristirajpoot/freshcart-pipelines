import pandas as pd
from sklearn.model_selection import train_test_split

# Mage injects these decorators at run time. Outside Mage (e.g. in CI) they
# are imported only if missing, with a no-op fallback if mage_ai isn't installed.
if 'transformer' not in globals():
    try:
        from mage_ai.data_preparation.decorators import transformer
    except ImportError:
        def transformer(func):
            return func
if 'test' not in globals():
    try:
        from mage_ai.data_preparation.decorators import test
    except ImportError:
        def test(func):
            return func


@transformer
def transform(df, *args, **kwargs):
    """Split the iris data 80/20 into train and test rows (adds a 'split' column)."""
    test_size = 0.2
    train_idx, test_idx = train_test_split(
        df.index, test_size=test_size, random_state=42, stratify=df['target']
    )
    out = df.copy()
    out['split'] = 'train'
    out.loc[test_idx, 'split'] = 'test'
    return out


@test
def test_output(output, *args) -> None:
    assert output is not None, 'The output is undefined'
    assert set(output['split'].unique()) == {'train', 'test'}
