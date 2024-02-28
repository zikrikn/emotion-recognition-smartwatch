import argparse
import glob
import yaml
import numpy as np
from collections import defaultdict
from sklearn import linear_model, metrics, model_selection, preprocessing
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.model_selection import RepeatedStratifiedKFold, GridSearchCV, RandomizedSearchCV
from scipy.stats import uniform, randint

SEED = 1
np.random.seed(SEED)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-mu", metavar='mu', type=str, nargs='+', help="file containing music features, input to model", default=[])
    parser.add_argument("-mw", metavar='mw', type=str, nargs='+', help="file containing music+walking features, input to model", default=[])
    parser.add_argument("-mo", metavar='mo', type=str, nargs='+', help="file containing movie features, input to model", default=[])
    parser.add_argument("-e", "--estimators", help="number of estimators for meta-classifiers", type=int, default=100)
    parser.add_argument("-o", "--output_file", help="output with pickle results", type=str, default="output")  
    parser.add_argument("--neutral", action='store_true', help="classify happy-sad-neutral")
    args = parser.parse_args()

    output_file = args.output_file
    N_ESTIMATORS = args.estimators
    neutral = args.neutral

    def process_condition(fnames, condition):
        if not fnames: 
            return
        print('condition', condition)

        results = {'labels':[], 'baseline': defaultdict(list),
                   'logit': defaultdict(list), 
                   'rf': defaultdict(list),
                   'svm': defaultdict(list)}  # Added SVM results

        for pattern in fnames:
            for fname in glob.glob(pattern):
                print('classifying:', fname)
                label = fname.split('/')[-1]

                data = np.loadtxt(fname, delimiter=',')
                print(data.shape)

                if not neutral:
                    data = np.delete(data, np.where(data[:,-1]==0), axis=0)

                np.random.shuffle(data)

                x_data = data[:,:-1]
                y_data = data[:,-1]

                x_data = preprocessing.scale(x_data)

                models = [
                    ('baseline', DummyClassifier(strategy='most_frequent')),
                    ('logit', linear_model.LogisticRegression(max_iter=10000)),
                    ('rf', RandomForestClassifier(n_estimators=N_ESTIMATORS)),
                    ('svm', SVC(gamma='auto', probability=True, max_iter=10000))  # Added probability=True for SVM classifier
                ]
                        
                results['labels'].append(label)
                repeats = 2  # Increase repeats
                folds = 2  # Increase folds
                rskf = RepeatedStratifiedKFold(n_splits=folds, 
                                            n_repeats=repeats,
                                            random_state=SEED)

                for key, clf in models:
                    # if key == 'svm':
                    #     param_grid = {'C': [0.1, 1, 10, 100], 'kernel': ['linear', 'rbf', 'poly', 'sigmoid']}
                    #     clf = GridSearchCV(SVC(gamma='auto', probability=True), param_grid, cv=rskf, scoring='accuracy')
                    if key == 'svm':
                        param_dist = {
                            'C': uniform(0.1, 10),  # Continuous uniform distribution for C
                            'kernel': ['linear', 'rbf', 'poly', 'sigmoid'],
                            'gamma': ['scale', 'auto']  # Distribution for gamma
                        }
                        clf = RandomizedSearchCV(SVC(probability=True), param_distributions=param_dist, n_iter=15, refit='accuracy', n_jobs=-1, verbose=0)
                    scores = {'f1':[], 'acc':[], 'roc_auc':[]}
                    for i, (train,test) in enumerate(rskf.split(x_data, y_data)):
                        x_train, x_test = x_data[train], x_data[test]
                        y_train, y_test = y_data[train], y_data[test]
                        clf.fit(x_train, y_train)
                        y_pred = clf.predict(x_test)
                        _f1 = metrics.f1_score(y_test, y_pred, average='weighted')
                        _acc = metrics.accuracy_score(y_test, y_pred)
                        if hasattr(clf, 'predict_proba'):
                            y_proba = clf.predict_proba(x_test)
                            if len(np.unique(y_test)) > 2:  # Multi-class scenario
                                _roc_auc = metrics.roc_auc_score(y_test, y_proba, average='weighted', multi_class='ovr')
                            else:  # Binary classification
                                _roc_auc = metrics.roc_auc_score(y_test, y_proba[:, 1], average='weighted', multi_class='ovr')
                            if not np.isnan(_roc_auc):
                                scores['roc_auc'].append(_roc_auc)

                        else:
                            _roc_auc = None
                        scores['f1'].append(_f1)
                        scores['acc'].append(_acc)

                    results[key]['f1'].append(np.mean(scores['f1']))
                    results[key]['acc'].append(np.mean(scores['acc']))
                    if scores['roc_auc']:  # Check if the list is not empty
                        results[key]['roc_auc'].append(np.mean(scores['roc_auc']))
                    else:
                        results[key]['roc_auc'].append(None)

        # yaml.dump(results, open(f"{condition}_lift_scores_{output_file}.yaml", 'w'))
        # yaml.dump(results, open(f"{condition}_lift_scores_hyper_{output_file}.yaml", 'w'))
        # yaml.dump(results, open(f"{condition}_coba_hyper_{output_file}.yaml", 'w'))
        yaml.dump(results, open(f"{condition}_coba1_hyper_{output_file}.yaml", 'w'))
        # yaml.dump(results, open(f"{condition}_feature_import_{output_file}.yaml", 'w'))

    if args.mu:
        process_condition(args.mu, 'mu')
    if args.mw:
        process_condition(args.mw, 'mw')
    if args.mo:
        process_condition(args.mo, 'mo')

if __name__ == "__main__":
    main()