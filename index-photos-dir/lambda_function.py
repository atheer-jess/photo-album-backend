import json
import urllib.parse
import boto3
import requests
import subprocess
import sys
# pip install custom package to /tmp/ and add to path
subprocess.call('pip install requests-aws4auth -t /tmp/ --no-cache-dir'.split(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
sys.path.insert(1, '/tmp/')
from requests_aws4auth import AWS4Auth
from datetime import datetime
"""
This function handles fulfillment for the SearchIntent in the
SearchPhotosBot. It collects up to two keywords from the user and sends
them to ElasticSearch to receive results, send back to users.
Jessica Kuleshov - jjk2235
Atheer Sami Alharbi - asa2259
"""

s3 = boto3.client('s3')
host = 'https://search-photos-metadata-hfbcmecj5hnuqzmgru4k6ahxai.us-east-1.es.amazonaws.com/' 
path = 'photos/_doc' # the OpenSearch API endpoint
region = 'us-east-1' # For example, us-west-1
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

url = host+path

def lambda_handler(event, context):

    # Get the object from the event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        rekog_labels = detect_labels(key, bucket) # Rekognition, getting labels

        object_metadata = s3.head_object(Bucket=bucket, Key=key)
        timestamp_dt = object_metadata['LastModified']
        timestamp = timestamp_dt.strftime("%Y-%m-%dT%H:%M:%S")

        labels = []
        meta_labels = object_metadata['ResponseMetadata']['HTTPHeaders'].get('x-amz-meta-customlabels')
        print(timestamp)
        if meta_labels is not None:
            if str(meta_labels):
                labels.append(meta_labels)
            else:
                labels = labels + meta_labels
                
        labels = labels + rekog_labels
        object_json = store_object_elastic(key, bucket, labels, timestamp) # getting JSON-formatted object. this should be returned to ElasticSearch!
        print("THIS IS OBJECT JSON: ", object_json)

    except Exception as e:
        print(e)
        print('Error getting object {} from bucket {}. Make sure they exist and your bucket is in the same region as this function.'.format(key, bucket))
        raise e


# AWS Rekognition - still need to implement proper roles and things
def detect_labels(photo, bucket):

    client=boto3.client('rekognition')

    response = client.detect_labels(Image={'S3Object':{'Bucket':bucket,'Name':photo}},
        MaxLabels=10)  # might change bounding on max labels

    label_names = []
    for label in response['Labels']:
        label_names.append(label['Name'].lower())
    return label_names


# index JSON object using ElasticSearch, returns JSON that has been indexed
def store_object_elastic(photo, bucket, labels, time):
    object_dict = {"objectKey": photo, "bucket": bucket, "createdTimestamp": time, "labels": labels}
    object_json = json.dumps(object_dict)
    
    headers = {'Content-type': 'application/json'}
    r = requests.post(url, auth=awsauth, json=object_dict, headers=headers)
    print("ElasticSearch response: ", r.text)
    return object_json
    
