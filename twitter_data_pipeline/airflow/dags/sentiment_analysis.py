from datetime import datetime, timedelta
from pymongo import MongoClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import text
from sqlalchemy import create_engine
from flair.models import TextClassifier
from flair.data import Sentence
from airflow import DAG
from airflow.operators.python_operator import PythonOperator


# connect to local MongoDB
client = MongoClient("mongodb", 27017)
db = client.tweets
tweets = db.tweets


# set parameters for local postgresDB
DATABASE_USER = "postgres"
DATABASE_PASSWORD = "postgres"
DATABASE_HOST = "postgresdb"
DATABASE_PORT = "5432"
DATABASE_DB_NAME = "postgres"

# connect to postgres
conns = f"postgres://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB_NAME}"
postgres_db = create_engine = create_engine(conns, encoding="utf-8")

# create table for twitter data from mongodb
create_query = """
CREATE TABLE IF NOT EXISTS tweets_sentiments (
tweet_id SERIAL PRIMARY KEY,
tweet_username VARCHAR(255),
tweet_text TEXT,
tweet_followers_count INTEGER,
tweet_timestamp TIMESTAMP,
tweet_location VARCHAR(255),
tweet_keyword VARCHAR(50),
tweet_neg REAL,
tweet_neu REAL,
tweet_pos REAL,
tweet_compound REAL,
tweet_flair_sentiment VARCHAR(20),
tweet_flair_score REAL
);
"""

# run query
postgres_db.execute(create_query)


def extract():
    """Extracts all tweets from the MongoDB database as a list"""
    # define a timestamp to only extract newest data
    last_extraction_date = datetime.utcnow() - timedelta(minutes=1)
    extracted_tweets = list(tweets.find({"timestamp": {"$gte": last_extraction_date}}))
    return extracted_tweets


def transform(**context):
    """
    Performs sentiment analysis on the tweets and returns it in a format so
    the tweets can be written into a Postgres database
    """
    extract_connection = context["ti"]
    extracted_tweets = extract_connection.xcom_pull(task_ids="extract")
    analyzer = SentimentIntensityAnalyzer()
    classifier = TextClassifier.load("sentiment")
    # For every tweet in extracted_tweets we want to perform sentiment analysis on the text
    transformed_tweets = []
    for tweet in extracted_tweets:
        vs = analyzer.polarity_scores(tweet["text"])
        sentence = Sentence(tweet["text"])
        classifier.predict(sentence)
        flair_sentiment = sentence.labels[0].value
        flair_sentiment_score = sentence.labels[0].score
        tweet["pos"] = vs["pos"]
        tweet["neu"] = vs["neu"]
        tweet["neg"] = vs["neg"]
        tweet["compound"] = vs["compound"]
        tweet["flair_sentiment"] = flair_sentiment
        tweet["flair_score"] = flair_sentiment_score
        transformed_tweets.append(tweet)
    return transformed_tweets


def load(**context):
    """Load transformed data into the Postgres database"""
    # extract data from context
    exctract_connection = context["ti"]
    transformed_tweets = exctract_connection.xcom_pull(task_ids="transform")

    insert_query = """
    INSERT INTO tweets_sentiments VALUES (
    DEFAULT, 
    :username, 
    :text, 
    :followers, 
    :timestamp, 
    :location, 
    :keyword, 
    :neg, 
    :neu, 
    :pos, 
    :compound, 
    :flair_sentiment, 
    :flair_score);"""

    # load data into postgres one by one
    for tweet in transformed_tweets:
        postgres_db.execute(
            text(insert_query),
            {
                "username": tweet["username"],
                "text": tweet["text"],
                "followers": tweet["followers_count"],
                "timestamp": tweet["timestamp"],
                "location": tweet["location"],
                "keyword": tweet["keyword"],
                "neg": tweet["neg"],
                "neu": tweet["neu"],
                "pos": tweet["pos"],
                "compound": tweet["compound"],
                "flair_sentiment": tweet["flair_sentiment"],
                "flair_score": tweet["flair_score"],
            },
        )


# define default arguments
default_args = {
    "owner": "Dennis",
    "start_date": datetime(2020, 7, 1),
    # 'end_date':
    "email": ["example@example.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}

# instantiate a DAG
dag = DAG(
    "sentiment_analysis",
    description="",
    catchup=False,
    schedule_interval=timedelta(minutes=1),
    default_args=default_args,
)

# define tasks
t1 = PythonOperator(task_id="extract", x_com_push=True, python_callable=extract, dag=dag)

t2 = PythonOperator(task_id="transform", provide_context=True, python_callable=transform, dag=dag)

t3 = PythonOperator(task_id="load", provide_context=True, python_callable=load, dag=dag)

# setup dependencies
t1 >> t2 >> t3
