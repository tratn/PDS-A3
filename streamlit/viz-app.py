import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests

# PAGE SIDEBAR
st.sidebar.title('Select the page to display visualisation')
app_mode = st.sidebar.selectbox('Select Page', ['Exploration', 'Prediction'])

# PAGE 1: EXPLORATION
if app_mode is 'Exploration':
    # BODY
    st.title('Exploration')
    st.subheader('Dataset')
    st.caption('The dataset contains responses from the 2020 Stack Overflow Developer survey, which is among the largest and most comprehensive survey of software developers. Below the first few rows of the dataset, together with the attributes that correspond to the questions included in the survey.')

    # DATAFRAME
    data = pd.read_csv('cleaned_data.csv')
    st.write(data.head())

    # CHART FOR DEMOGRAPHIC FACTOR
    st.subheader('Demographic of survey respondents')
    demo_factor = st.selectbox('Select demographic factor to explore', [
        'Age', 'Employment', 'Education', 'Undergraduate Major'])

    # plot the data
    if demo_factor == 'Age':
        fig = go.Figure(
            data=[go.Histogram(
                x=data['Age'],
            )])
        xlabel = 'Age'
        ylabel = 'Frequency'
        title = 'Age distribution among survey respondents'

    elif demo_factor == 'Employment':
        fig = go.Figure(data=[go.Bar(
            x=data['Employment'].value_counts(), y=data['Employment'].value_counts().index.tolist(), orientation='h',
        )])
        xlabel = 'Frequency'
        ylabel = 'Employment status'
        title = 'Employment status among survey respondents'

    elif demo_factor == 'Undergraduate Major':
        fig = go.Figure(data=[go.Bar(
            x=data['UndergradMajor'].value_counts(), y=data['UndergradMajor'].value_counts().index.tolist(), orientation='h',
        )])
        xlabel = 'Frequency'
        ylabel = 'Major'
        title = 'Undergraduate major among survey respondents'

    elif demo_factor == 'Education':
        fig = go.Figure(data=[go.Pie(labels=list(data['EdLevel'].value_counts().index), values=data['EdLevel'].value_counts(), hoverinfo="label+percent",
                                     )])
        xlabel = None
        ylabel = None
        title = 'Education level among survey respondents'

    # plot styling
    fig.update_layout(
        title=title,
        xaxis_title=xlabel,
        yaxis_title=ylabel,
        margin=dict(
            pad=10,
        ),
        yaxis=dict(
            showgrid=False
        ),
        xaxis=dict(
            showgrid=False
        ),
        showlegend=False
    )
    # display plot
    st.plotly_chart(fig)

    # CHART FOR COLUMN PAIR 1
    st.subheader('Working hours and Job satisfaction')
    # get the data
    workhrs_jobsat = data.loc[:, ['WorkWeekHrs', 'JobSat']]
    # plot the data
    fig = go.Figure()
    jobsat = ['very satisfied', 'very dissatisfied']
    for jobsat_type in jobsat:
        fig.add_trace(go.Violin(
            y=data['JobSat'][data['JobSat'] == jobsat_type],
            x=data['WorkWeekHrs'][data['JobSat'] == jobsat_type],
            name=jobsat_type,
            box_visible=True,
            meanline_visible=True)
        )
    # plot styling
    fig.update_layout(
        title_text='Total working hours per week and job satisfaction level',
        xaxis_title='Weekly working hours',
        yaxis_title='Job statisfaction level',
        margin=dict(
            pad=10
        ),
        yaxis=dict(
            showgrid=False
        ),
        xaxis=dict(
            showgrid=False
        ),
        showlegend=False)

    fig.update_traces(orientation='h')  # horizontal box plots

    # display the plot
    st.plotly_chart(fig)

    # explain for the plot
    st.write("There have been many research studies looking at impact of working hours on employee's job satisfaction. For an average person, the total number of weekly working hours is estimated to be around 40. Looking at most dense region of the violin plot, we can see that majority survey respondents work around 40 hours per week.")
    st.write("The upper adjacent values for 'very satisfied' and 'very dissatisfied' are 40 and 50 respectively. This shows that those who feel dissatisfied at their job tends to have longer working hours.")

    # CHART FOR COLUMN PAIR 2
    st.subheader('Job Factors and Gender')
    st.write('Different genders might have different values and workplace expectations. The chart below shows some of the most important job factors for each gender type.')

    # get the data
    jobfact = data['JobFactors'].str.get_dummies(sep=';')
    jobfact_gender = jobfact.join(data['Gender'])
    jobfact_gender = jobfact_gender.drop(
        jobfact_gender[(jobfact.notmentioned == 1)].index)
    jobfact_gender.drop(columns='notmentioned', inplace=True)

    # transform the data
    def counts_per_group(df, col, group, options):
        values = df[df.loc[:, col] == group]
        d = {}
        for option in options:
            count = values[option].sum(axis=0)
            d[option] = count
            d = dict(sorted(d.items(), key=lambda item: item[1]))
        results = pd.DataFrame(list(d.items())[:])
        results = results.set_index(0)
        return results

    factors = jobfact_gender.columns.tolist()
    factors.remove("Gender")
    jobfactors_man = counts_per_group(jobfact_gender, 'Gender', 'man', factors)
    jobfactors_woman = counts_per_group(
        jobfact_gender, 'Gender', 'woman', factors)
    jobfactors_nonbinary = counts_per_group(
        jobfact_gender, 'Gender', 'non-binary, genderqueer, or gender non-conforming', factors)

    # plot the data based on selected option
    gender_options = st.selectbox('View by gender type', [
        'Man', 'Woman', 'Non-binary, genderqueer, or gender non-conforming'])

    if gender_options == 'Man':
        fig = go.Figure(data=[go.Bar(
            x=jobfactors_man.iloc[:, 0].values, y=jobfactors_man.iloc[:, 0].index.tolist(), orientation='h',
        )])

    elif gender_options == 'Woman':
        fig = go.Figure(data=[go.Bar(
            x=jobfactors_woman.iloc[:, 0].values, y=jobfactors_woman.iloc[:, 0].index.tolist(), orientation='h',
        )])
    elif gender_options == 'Non-binary, genderqueer, or gender non-conforming':
        fig = go.Figure(data=[go.Bar(
            x=jobfactors_nonbinary.iloc[:, 0].values, y=jobfactors_nonbinary.iloc[:, 0].index.tolist(), orientation='h',

        )])

    # plot styling
    fig.update_layout(
        title_text='Most important job factors by gender',
        width=800,
        height=500,
        margin=dict(
            pad=10,
        ),
        yaxis=dict(
            showgrid=False
        ),
        xaxis=dict(
            showgrid=False
        ),
        showlegend=False
    )
    # display the plot
    st.plotly_chart(fig)

    # explain the plot
    st.write("As can be seen from the graph, having flexibile work time/schedule is the second most important job factor among the three gender representations. Majority of male survey respondents consider the language/framework they work with to be most important job factor. On the contrary, female and non-binary/genderqueer/gender non-conforming respondents identify office environment and company culture to be most important.")

# PAGE 2: PREDICTiON
elif app_mode is 'Prediction':
    st.title('Multi-label classification')

    # PREDICTION
    st.subheader('Prediction')
    # get the data from flask api
    pred_url = 'http://127.0.0.1:5000/predict'
    pred_res = requests.post(pred_url)
    pred_data = pred_res.json()['prediction']
    pred_df = pd.DataFrame(pred_data, columns=['Predicted income category'])

    # display the prediction
    st.write(pred_df.head())

    # option to download prediction output as csv file

    @st.cache
    def df_to_csv(df):
        return df.to_csv().encode('utf-8')

    csv = df_to_csv(pred_df)

    st.download_button(
        label="Download prediction as CSV",
        data=csv,
        file_name='predictions.csv',
        mime='text/csv',
    )

    # EVALUATION
    st.subheader('Evaluation metrics')
    # get the data from flask api
    eval_url = 'http://127.0.0.1:5000/evaluate'
    eval_res = requests.post(eval_url)
    eval_data = eval_res.json()
    # display the metrics
    col1, col2 = st.columns(2)
    col1.metric(label="Accuracy", value="{0:.4f}".format(
        eval_data['accuracy']))
    col2.metric(label="Precision", value="{0:.4f}".format(
        eval_data['precision']))
    st.write('Confusion Matrix')
    st.write(eval_data['confusion matrix'])

    # display classification report

    cf_report_cat1 = pd.json_normalize(
        eval_data['classification_report']['< 25k'])
    cf_report_cat2 = pd.json_normalize(
        eval_data['classification_report']['< 50k'])
    cf_report_cat3 = pd.json_normalize(
        eval_data['classification_report']['< 100k'])
    cf_report_cat4 = pd.json_normalize(
        eval_data['classification_report']['> 100k'])

    st.subheader('Classification report')
    st.write('Income category: 0 to under 25,000 USD')
    st.write(cf_report_cat1)
    st.write('Income category: 25,000 to under 50,000 USD')
    st.write(cf_report_cat2)
    st.write('Income category: 50,000 to under 100,000 USD')
    st.write(cf_report_cat3)
    st.write('Income category: above 100,000 USD ')
    st.write(cf_report_cat4)

    # CHART
    st.subheader('Chart')
    pred_options = st.selectbox('Select chart option to display', [
        'Years of coding', 'Developer type', 'Languages/frameworks', 'Education Level'])

    # prepare prediction data to plot
    income_cat = pred_df['Predicted income category'].value_counts(
    ).index.tolist()
    frequencies = pred_df['Predicted income category'].value_counts(
    ).values

    # plot the data
    fig = go.Figure(data=[go.Scatter(
        x=income_cat, y=frequencies,
        mode='markers',
        marker=dict(
            color=['rgb(93, 164, 214)', 'rgb(255, 144, 14)',
                   'rgb(44, 160, 101)', 'rgb(255, 65, 54)'],
            size=frequencies/20,

        )
    )])

    fig.update_layout(
        title_text='Total counts for predicted income category',
        xaxis_title='Income category',
        yaxis_title='Frequency',
        width=800,
        height=500,
        margin=dict(
            pad=10,
        ),
        yaxis=dict(
            showgrid=False
        ),
        xaxis=dict(
            showgrid=False
        ),
        showlegend=False
    )

    # display the plot
    st.plotly_chart(fig)
