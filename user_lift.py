import argparse
import sys
import yaml
import numpy as np
from collections import defaultdict

from sklearn import linear_model
from sklearn import metrics
from sklearn import model_selection
from sklearn import preprocessing

from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.gaussian_process import GaussianProcessClassifier
from sklearn.model_selection import RepeatedStratifiedKFold

from permute.core import one_sample

SEED = 1
np.random.seed(SEED)

def main():
    '''
    Run as:
    python classify.py chi/features_*

    Takes features generated by extract_windows.py script, runs classifier, and prints accuracy results.
    '''
    parser = argparse.ArgumentParser()
    parser.add_argument("-mu", metavar='mu', type=str, nargs='+', help="file containing music features, input to model", default=[])
    parser.add_argument("-mw", metavar='mw', type=str, nargs='+', help="file containing music+walking features, input to model", default=[])
    parser.add_argument("-mo", metavar='mo', type=str, nargs='+', help="file containing movie features, input to model", default=[])
    parser.add_argument("-e", "--estimators", help="number of estimators for meta-classifiers", type=int, default=100)
    parser.add_argument("-o", "--output_file", help="output with pickle results", type=str)
    parser.add_argument("--neutral", action='store_true', help="classify happy-sad-neutral")
    args = parser.parse_args()
    output_file = args.output_file
    N_ESTIMATORS = args.estimators
    neutral = args.neutral


    def process_condition(fnames, condition):

        if not fnames: 
            return
        print 'condition', condition

        results = {'labels':[], 'baseline': defaultdict(list),
                    'logit': defaultdict(list), 
                    'rf': defaultdict(list)}

        for fname in fnames:
            print 'classifying: %s' % fname
            label = fname.split('/')[-1]

            data = np.loadtxt(fname, delimiter=',')

            # only acc: acc + y_label as column vector
            #data = np.hstack([data[:,:51], data[:,-1].reshape(data.shape[0], 1)])

            # acc features + heart rate + y label
            #data = np.hstack([data[:,:51], data[:,-2:]])
            print data.shape

            scoring = 'roc_auc'
            if not neutral:
                # delete neutral to see if we can distinguish between
                # happy/sad
                data = np.delete(data, np.where(data[:,-1]==0), axis=0)

            # detect neutral vs emotion
            #data[data[:,-1]!=0,-1] = 1

            np.random.shuffle(data)

            x_data = data[:,:-1]
            y_data = data[:,-1]

            # scaled
            x_data = preprocessing.scale(x_data)

            #_cv = model_selection.LeaveOneOut()
            _cv = 10

            models = [
                    ('baseline', DummyClassifier(strategy = 'most_frequent')),
                    #('logit', linear_model.LogisticRegressionCV(Cs=20, cv=10)),
                    ('logit', linear_model.LogisticRegression()),
                    ('rf', RandomForestClassifier(n_estimators = N_ESTIMATORS)),
                    #('gp', GaussianProcessClassifier()),
                    ]
                    
            results['labels'].append(label)
            repeats = 10
            folds = 10
            rskf = RepeatedStratifiedKFold(n_splits=folds, 
                                        n_repeats=repeats,
                                        random_state=SEED)

            for key, clf in models:
                scores = {'f1':[], 'acc':[], 'roc_auc':[]}
                for i, (train,test) in enumerate(rskf.split(x_data, y_data)):
                    x_train, x_test = x_data[train], x_data[test]
                    y_train, y_test = y_data[train], y_data[test]
                    clf.fit(x_train, y_train)
                    y_pred = clf.predict(x_test)
                    _f1 = metrics.f1_score(y_test, y_pred, average='weighted')
                    _acc = metrics.accuracy_score(y_test, y_pred)
                    y_proba = clf.predict_proba(x_test)
                    _roc_auc = metrics.roc_auc_score(y_test, y_proba[:, 1], average='weighted')
                    scores['f1'].append(_f1)
                    scores['acc'].append(_acc)
                    scores['roc_auc'].append(_roc_auc)

                #results[key] = {'f1': np.mean(scores['f1']), 'acc': np.mean(scores['acc']), 'f1_all': scores['f1'], 'acc_all':scores['acc']}
                results[key]['f1'].append(np.mean(scores['f1']))
                results[key]['acc'].append(np.mean(scores['acc']))
                results[key]['roc_auc'].append(np.mean(scores['roc_auc']))

                #score = model_selection.cross_val_score(clf, x_data, y_data, cv=_cv, scoring='accuracy', n_jobs=2)
                #results[key].append(score.mean())
                #print key, 'f1', np.mean(scores['f1'])
                #print key, 'acc', np.mean(scores['acc'])
                #print key, 'roc_auc', np.mean(scores['roc_auc'])


        #for key, model in models:
        #    print key, np.mean(results[key]), np.std(results[key])

        yaml.dump(results, open(condition+'_lift_scores_'+output_file+'.yaml', 'w'))
    # end of function
    #---------
    if args.mu:
        process_condition(args.mu, 'mu')
    if args.mw:
        process_condition(args.mw, 'mw')
    if args.mo:
        process_condition(args.mo, 'mo')


if __name__ == "__main__":
    main()
