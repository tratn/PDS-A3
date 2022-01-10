import os
import pickle
import pandas as pd
import numpy as np

from sklearn import preprocessing
from sklearn.model_selection import KFold
from flask import Flask, jsonify, request, render_template
from sklearn.metrics import classification_report
from sklearn.metrics import confusion_matrix

MODEL_PATH = "pickle_model.pkl"
with open(MODEL_PATH, "rb") as rf:
    clf = pickle.load(rf)

# Preprocessing data

def preprocessing_data():
    ### READ DATA
    url = 'survey_results_public.csv'
    preprocess = pd.read_csv(url, sep=',')

    ### MISSING VALUE
    # list of mandatory columns.
    # 'RespodentID' is assigned automatically, hence not included in this list
    mandatory_cols = ['MainBranch', 'Hobbyist', 'Country',
                      'CurrencyDesc', 'CurrencySymbol', 'JobSeek']
    preprocess.dropna(subset=mandatory_cols, inplace=True)
    # drop missing values for CompFreq
    preprocess.dropna(subset=['CompFreq', 'CompTotal'], axis=0, inplace=True)

    dkk_to_usd = 138936.0/80000.0
    converted_comp = preprocess.loc[preprocess.index.isin(
        [47224]), 'CompTotal']*dkk_to_usd
    # fill the missing converted compensation
    preprocess.loc[preprocess.index.isin(
        [47224]), 'ConvertedComp'] = converted_comp
    # fix the currency symbol
    preprocess.loc[preprocess.index.isin(
        [47224]), 'CurrencyDesc'] = 'Faroese krona'
    preprocess.loc[preprocess.index.isin([47224]), 'CurrencySymbol'] = 'KR'
    # drop missing values for Cook Island dollar
    cols_to_drop = preprocess[preprocess.loc[:,
                                             'ConvertedComp'].isnull() == True].index.tolist()
    preprocess.drop(index=cols_to_drop, inplace=True)
    # fill missing age and working hours with median
    med_age = preprocess['Age'].median()
    med_hour = preprocess['WorkWeekHrs'].median()
    preprocess.fillna({'Age': med_age, 'WorkWeekHrs': med_hour}, inplace=True)
    # fill other columns with 'NotMentioned'
    cat_cols = preprocess.select_dtypes(include=[object]).columns.tolist()
    preprocess[cat_cols] = preprocess[cat_cols].fillna(value='NotMentioned')

    ### WHITESPACES/STRING MANIPULATION
    # remove whitespace
    preprocess = preprocess.apply(
        lambda x: x.str.strip() if x.dtype == "object" else x)
    # transform letter to lowercase
    preprocess = preprocess.apply(
        lambda x: x.str.lower() if x.dtype == "object" else x)
    
    # Replace highest/lowest values with the corresponding float value
    # Replace 'notmentioned' values with the MODE value
    preprocess['Age1stCode'] = preprocess['Age1stCode'].replace("younger than 5 years", "4")
    preprocess['Age1stCode'] = preprocess['Age1stCode'].replace("older than 85", "86")
    preprocess['Age1stCode'] = preprocess['Age1stCode'].replace("notmentioned", "14")

    preprocess['YearsCode'] = preprocess['YearsCode'].replace("less than 1 year", "0.5")
    preprocess['YearsCode'] = preprocess['YearsCode'].replace("more than 50 years", "51")
    preprocess['YearsCode'] = preprocess['YearsCode'].replace("notmentioned", "10")

    preprocess['YearsCodePro'] = preprocess['YearsCodePro'].replace("less than 1 year", "0.5")
    preprocess['YearsCodePro'] = preprocess['YearsCodePro'].replace("more than 50 years", "51")
    preprocess['YearsCodePro'] = preprocess['YearsCodePro'].replace("notmentioned", "3")
    
    # Cast 'Age1stCode', 'YearsCode', 'YearsCodePro' to float type
    for col in ['Age1stCode', 'YearsCode', 'YearsCodePro']:
        preprocess[col] = preprocess[col].astype('float64')

    ## EXTREME VALUE AND OUTLIERS
    preprocess.drop(preprocess[preprocess['Age1stCode'] > preprocess['Age']].index, inplace = True)
    preprocess.drop(preprocess[preprocess['YearsCodePro'] > preprocess['YearsCode']].index, inplace = True)
    # Outliers
    outliers_df = preprocess.loc[(preprocess['Age'] > 80) | (preprocess['Age1stCode'] > 75)]
    preprocess.drop(outliers_df.index, inplace = True)
    # Impossible value
    preprocess[preprocess['YearsCode'] > preprocess['Age']]
    preprocess.loc[preprocess['YearsCode'] > preprocess['Age'], ['Age']] = preprocess['YearsCode'] + preprocess['Age1stCode']
    preprocess.drop(preprocess.loc[preprocess['WorkWeekHrs'] > (24*7)].index, inplace=True)
    # generate copy of ConvertedComp column
    preprocess["ConvertedComp_Copy"] = preprocess["ConvertedComp"]
    
    # Create categories for compensation
    preprocess["ConvertedComp"] = pd.cut(preprocess["ConvertedComp"],
                                         bins=[0, 24000, 48000,
                                               96000, np.inf],
                                         labels=['0-24k', '24k-48k', '48k-96k', '>96k'],
                                         include_lowest=True)

    ## 'NEWOvertime' feature
    # drop non-meaning value
    preprocess = preprocess[preprocess.NEWOvertime != 'notmentioned']
    # convert columns to categories
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].astype('category')
    # adding new categories
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].cat.add_categories(
        '0')
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].cat.add_categories(
        '1')
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].cat.add_categories(
        '2')
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].cat.add_categories(
        '3')
    preprocess['NEWOvertime'] = preprocess['NEWOvertime'].cat.add_categories(
        '4')
    # classifying the suitable entries
    preprocess.loc[(preprocess['NEWOvertime'].isin(["never"])),
                   ['NEWOvertime']] = "0"
    preprocess.loc[(preprocess['NEWOvertime'].isin(
        ["rarely: 1-2 days per year or less"])), ['NEWOvertime']] = "1"
    preprocess.loc[(preprocess['NEWOvertime'].isin(
        ["occasionally: 1-2 days per quarter but less than monthly"])), ['NEWOvertime']] = "2"
    preprocess.loc[(preprocess['NEWOvertime'].isin(
        ["sometimes: 1-2 days per month but less than weekly"])), ['NEWOvertime']] = "3"
    preprocess.loc[(preprocess['NEWOvertime'].isin(
        ["often: 1-2 days per week or more"])), ['NEWOvertime']] = "4"
    # converting the columns' datatypes to numeric
    preprocess["NEWOvertime"] = pd.to_numeric(
        preprocess["NEWOvertime"], errors='raise')

    ### LABEL ENCODING FOR BETTER PREDICT
    label_encoder = preprocessing.LabelEncoder()
    # Transform data

    def label_encode(column, dataset):
        dataset[column] = label_encoder.fit_transform(dataset[column])

    ## Encode labels in columns.
    LabEnArr = ['Country', 'Employment', 'CompFreq',
                'OpSys', 'OrgSize', 'EdLevel', 'MainBranch']
    for i in LabEnArr:
        label_encode(i, preprocess)

    ### CREATE NEW FEATURES FROM 'DevType'
    # method to check if the user have specific role that we want
    def get_DevType(type, data):
        column = 'DevType_' + type
        data['DevType_' + type] = data['DevType'].copy()
        data.loc[data[column].str.contains(type), column] = True
        data[column] = np.where(data[column].isin([True]), data[column], False)
        data[column] = data[column].astype(bool)
    # choose which type of developer that we need
    DevTypeArr = ['academic researcher', 'data or business analyst', 'data scientist or machine learning specialist', 'database administrator',
                  'designer', 'developer', 'devops specialist', 'educator', 'engineer', 'engineering manager', 'marketing or sales professional',
                  'product manager', 'scientist', 'senior executive', 'system administrator']
    # create new features
    for i in DevTypeArr:
        get_DevType(i, preprocess)
    # copy DevType features to new dataframe
    DevType_df = preprocess.loc[:,
                                preprocess.columns.str.startswith('DevType_')]

    ### MERGE DATESET WITH NEW FEATURES AND SPLIT THE DATASET FOR TESTING API
    # split X, y
    X = preprocess[['MainBranch', 'Country', 'Employment', 'CompFreq', 'OpSys', 'OrgSize', 'EdLevel', 'WorkWeekHrs',
                    'Age', 'YearsCode', 'YearsCodePro', 'NEWOvertime']]
    y = preprocess['ConvertedComp']
    # merge devtype features with remaining data
    X = pd.concat([X, DevType_df], axis=1)

    return X, y


def cross_val(X, y):
    # KFold cross-validation for split data
    kf = KFold(n_splits=5, random_state=42, shuffle=True)
    for train_index, test_index in kf.split(X, y):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]
    return X_test, y_test


# Init the app
app = Flask(__name__)


@app.route('/')
def home():
    return render_template('index.html')

# predict function


def predict_function(clf):
    y_pred = clf.predict(X_test)
    return y_pred


# Predict function api
@app.route("/predict", methods=['POST'])
def predict():
    predictions = predict_function(clf)

    result = {
        'prediction': list(predictions)
    }

    return result


# evaluate function
def evaluate_function(model):
    # predict
    y_pred = clf.predict(X_test)

    # evaluate
    from sklearn.metrics import accuracy_score
    from sklearn.metrics import precision_score
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average='macro')
    report = classification_report(y_test, y_pred, output_dict=True)
    matrix = confusion_matrix(y_test, y_pred)

    return accuracy, precision, report, matrix


# evaluate function api
@app.route("/evaluate", methods=['POST'])
def evaluate():
    accuracy, precision, report, matrix = evaluate_function(clf)
    matrix = pd.DataFrame(matrix).to_json(orient='values')
    result = {
        "accuracy": accuracy,
        "precision": precision,
        "classification_report": report,
        "confussion matrix": matrix
    }
    return jsonify(result)


# main
if __name__ == '__main__':
    X, y = preprocessing_data()
    X_test, y_test = cross_val(X, y)
    app.run(debug=True)