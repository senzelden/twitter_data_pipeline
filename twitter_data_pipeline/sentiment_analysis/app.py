import pymongo
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from sqlalchemy import text
from sqlalchemy import create_engine


# connect to local MongoDB
client = pymongo.MongoClient('mongodb', 27017)
db = client.tweets
tweets = db.tweets

DATABASE_USER = 'denniss'
DATABASE_PASSWORD = 'postgres'
DATABASE_HOST = 'postgresdb'
DATABASE_PORT = '5432'
DATABASE_DB_NAME = 'postgres'

conns = f'postgres://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB_NAME}'
postgres_db = create_engine = create_engine(conns, encoding='utf-8')
create_query = """
CREATE TABLE IF NOT EXISTS tweets_sentiments (
tweet_id SERIAL PRIMARY KEY,
tweet_username VARCHAR(255),
tweet_text TEXT,
tweet_followers_count INTEGER,
tweet_timestamp TIMESTAMP,
tweet_neg REAL,
tweet_neu REAL,
tweet_pos REAL,
tweet_compound REAL
);
"""

postgres_db.execute(create_query)

analyzer = SentimentIntensityAnalyzer()
for tweet in tweets.find():
    vs = analyzer.polarity_scores(tweet['text'])
    insert_query = """INSERT INTO tweets_sentiments VALUES (DEFAULT, :username, :text, :followers, :timestamp, :neg, :neu, :pos, :compound);"""
    postgres_db.execute(text(insert_query), {'username': tweet['username'], 'text': tweet['text'], 'followers': tweet['followers_count'], 'timestamp': tweet['timestamp'], 'neg': vs['neg'], 'neu': vs['neu'], 'pos': vs['pos'], 'compound': vs['compound']})
