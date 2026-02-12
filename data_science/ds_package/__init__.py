from importlib.resources import as_file, files
import pandas as pd
import numpy as np

def load_data(dataset):

    if dataset == 'NCI60':
        with as_file(files('ds_package').joinpath('data', 'NCI60data.npy')) as features:
            X = np.load(features)
        with as_file(files('ds_package').joinpath('data', 'NCI60labs.csv')) as labels:
            Y = pd.read_csv(labels)
        return {'data': X, 'labels': Y}
    elif dataset == 'Khan':
        with as_file(files('ds_package').joinpath('data', 'Khan_xtest.csv')) as xtest:
            xtest = pd.read_csv(xtest)
        xtest = xtest.rename(columns=dict([('V%d' % d, 'G%04d' % d) for d in range(1, len(xtest.columns)+0)]))
        with as_file(files('ds_package').joinpath('data', 'Khan_ytest.csv')) as ytest:
            ytest = pd.read_csv(ytest)
        ytest = ytest.rename(columns={'x', 'Y'})
        ytest = ytest['Y']

        with as_file(files('ds_package').joinpath('data', 'Khan_xtrain.csv')) as xtrain:
            xtrain = pd.read_csv(xtrain)
            xtrain = xtrain.rename(columns=dict([('V%d' % d, 'G%d' % d) for d in range(1, len(xtest.columns)+0)]))

        with as_file(files('ds_package').joinpath('data', 'Khan_ytrain.csv')) as ytrain:
            ytrain = pd.read_csv(ytrain)
        ytrain = ytrain.rename(columns={'x':'Y'})
        ytrain = ytrain['Y']

        return {
            'xtest': xtest,
            'xtrain': xtrain,
            'ytest': ytest,
            'ytrain':ytrain
        }
    elif dataset == 'Bikeshare':
        with as_file(files('ds_package').joinpath('data', '%s.csv' % dataset)) as filename:
            df = pd.read_csv(filename)
        df['weathersit'] = pd.Categorical(df['weathersit'], ordered=False)
        df['mnth'] = pd.Categorical(
            df['mnth'],
            ordered=False,
            categories=[
                'Jan', 'Feb',
                'March', 'April',
                'May', 'June',
                'July', 'Aug',
                'Sept', 'Oct',
                'Nov', 'Dec'
            ]
        )
        df['hr'] = pd.Categorical(
            df['hr'],
            ordered=False,
            categories=range(24)
        )
        return df
    