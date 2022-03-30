import json
import boto3
import urllib.parse
import subprocess
import sys
# pip install custom package to /tmp/ and add to path
subprocess.call('pip install requests-aws4auth -t /tmp/ --no-cache-dir'.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.call('pip install requests -t /tmp/ --no-cache-dir'.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')
import requests
from requests_aws4auth import AWS4Auth
from datetime import datetime
"""
This function handles fulfillment for the SearchIntent in the
SearchPhotosBot. It collects up to two keywords from the user and sends
them to ElasticSearch to receive results, send back to users.
Jessica Kuleshov - jjk2235
Atheer Sami Alharbi - asa2259
"""
host = 'https://search-photos-metadata-hfbcmecj5hnuqzmgru4k6ahxai.us-east-1.es.amazonaws.com/' 
path = 'photos/_search' # the OpenSearch API endpoint
region = 'us-east-1' # For example, us-west-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

url = host + path


def lambda_handler(event, context):
    input = event['q']
    client = boto3.client('lex-runtime')
    data = "string input"
    response = client.post_text(
    botName='SearchPhotosBot',
    botAlias='search_photos_bot',
    userId='id',
    inputText= input)
    print("THIS IS RESPONSE: ", response)
    keywordOne = response['slots']['keywordOne']
    keywordTwo = response['slots']['keywordTwo']
    print("How are you!")

    keywords = [keywordOne]
    if keywordTwo is not None:
        keywords.append(keywordTwo)
    photo_keys = get_matching_photos(keywords)
    
    return photo_keys


# search the keywords in ElasticSearch to get matching photos, if any
def get_matching_photos(keywords):
    result_keys = []
    for keyword in keywords:
        # Match category in Elastic Search
        query ={
                "query":{
                    "function_score": {
                        "query": { 
                            "match": {
                              "labels"  : keyword
                              }},
                        "boost": "5",
                        "random_score": {}, 
                        "boost_mode": "multiply"
              
        }
    
                }, "size": 2}
                
        # Perform the search in Elastic Search
        r = requests.get(url, auth=awsauth, json=query)
        req = r.json()
        poss_hit_1 = req.get("hits")
        if poss_hit_1 is not None:
            poss_hits = req["hits"].get("hits")
            if poss_hits is not None:
                for hit in poss_hits:
                    if hit["_source"]["objectKey"] not in result_keys:
                        result_keys.append(hit["_source"]["objectKey"])
    return result_keys
