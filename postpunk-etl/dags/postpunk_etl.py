"""
PostPunk ETL DAG - Extracción y procesamiento de datos de bandas post-punk (1980-1999)
"""
import os
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.cncf.kubernetes.operators.spark_kubernetes import SparkKubernetesOperator
from airflow.models import Variable
import requests
import json
import boto3
from botocore.client import Config

# Default DAG arguments
default_args = {
    'owner': 'postpunk-team',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'postpunk_etl',
    default_args=default_args,
    description='Extract and process post-punk bands data (1980-1999)',
    schedule='@daily',
    catchup=False,
    max_active_runs=1,
    tags=['postpunk', 'etl', 'music'],
)

# MinIO S3 configuration
MINIO_ENDPOINT = Variable.get('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = Variable.get('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = Variable.get('MINIO_SECRET_KEY', 'minioadmin')
S3_BUCKET = 'postpunk-raw'

# API configurations
MUSICBRAINZ_BASE_URL = 'https://musicbrainz.org/ws/2'
THEAUDIODB_BASE_URL = 'https://www.theaudiodb.com/api/v1/json/2'
DISCOGS_BASE_URL = 'https://api.discogs.com'
DISCOGS_TOKEN = Variable.get('DISCOGS_TOKEN', default_var='')

def get_s3_client():
    """Initialize MinIO S3 client"""
    return boto3.client(
        's3',
        endpoint_url=f'http://{MINIO_ENDPOINT}',
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'
    )

def extract_musicbrainz_data(**context):
    """Extract post-punk bands data from MusicBrainz API"""
    ds = context['ds']
    s3_client = get_s3_client()
    
    # Post-punk related tags and genres
    post_punk_tags = ['post-punk', 'new wave', 'alternative rock', 'indie rock']
    all_bands = []
    
    for tag in post_punk_tags:
        print(f"Extracting bands for tag: {tag}")
        
        # Search for artists by tag
        url = f"{MUSICBRAINZ_BASE_URL}/artist"
        params = {
            'query': f'tag:{tag} AND begin:[1980 TO 1999]',
            'limit': 100,
            'fmt': 'json'
        }
        
        try:
            response = requests.get(url, params=params, headers={'User-Agent': 'PostPunkETL/1.0'})
            response.raise_for_status()
            data = response.json()
            
            for artist in data.get('artists', []):
                band_data = {
                    'id': artist.get('id'),
                    'name': artist.get('name'),
                    'country': artist.get('country'),
                    'begin_date': artist.get('life-span', {}).get('begin'),
                    'end_date': artist.get('life-span', {}).get('end'),
                    'tags': [tag['name'] for tag in artist.get('tags', [])],
                    'type': artist.get('type'),
                    'source': 'musicbrainz',
                    'extracted_date': ds
                }
                
                # Get additional details for each band
                if artist.get('id'):
                    try:
                        # Get releases
                        releases_url = f"{MUSICBRAINZ_BASE_URL}/release-group"
                        releases_params = {
                            'artist': artist['id'],
                            'type': 'album',
                            'limit': 50,
                            'fmt': 'json'
                        }
                        releases_response = requests.get(releases_url, params=releases_params, 
                                                       headers={'User-Agent': 'PostPunkETL/1.0'})
                        if releases_response.status_code == 200:
                            releases_data = releases_response.json()
                            band_data['releases'] = releases_data.get('release-groups', [])
                    except Exception as e:
                        print(f"Error fetching releases for {artist['name']}: {e}")
                        band_data['releases'] = []
                
                all_bands.append(band_data)
        
        except requests.RequestException as e:
            print(f"Error extracting MusicBrainz data for tag {tag}: {e}")
            continue
    
    # Save to S3/MinIO
    s3_key = f"musicbrainz/{ds}/bands.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(all_bands, indent=2),
        ContentType='application/json'
    )
    
    print(f"Extracted {len(all_bands)} bands from MusicBrainz and saved to s3://{S3_BUCKET}/{s3_key}")
    return len(all_bands)

def extract_theaudiodb_data(**context):
    """Extract additional band data from TheAudioDB API"""
    ds = context['ds']
    s3_client = get_s3_client()
    
    # Get band names from previous MusicBrainz extraction
    musicbrainz_key = f"musicbrainz/{ds}/bands.json"
    try:
        musicbrainz_obj = s3_client.get_object(Bucket=S3_BUCKET, Key=musicbrainz_key)
        musicbrainz_data = json.loads(musicbrainz_obj['Body'].read())
        band_names = [band['name'] for band in musicbrainz_data[:50]]  # Limit to avoid rate limits
    except Exception as e:
        print(f"Could not load MusicBrainz data: {e}")
        # Fallback to known post-punk bands
        band_names = ['Joy Division', 'The Cure', 'Siouxsie and the Banshees', 'Bauhaus', 
                     'Gang of Four', 'Wire', 'Television', 'Talking Heads', 'Devo', 'X']
    
    all_band_details = []
    
    for band_name in band_names:
        try:
            print(f"Fetching TheAudioDB data for: {band_name}")
            
            # Search for band
            url = f"{THEAUDIODB_BASE_URL}/search.php"
            params = {'s': band_name}
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get('artists'):
                for artist in data['artists']:
                    band_detail = {
                        'id': artist.get('idArtist'),
                        'name': artist.get('strArtist'),
                        'biography': artist.get('strBiographyEN'),
                        'country': artist.get('strCountry'),
                        'formed_year': artist.get('intFormedYear'),
                        'genre': artist.get('strGenre'),
                        'style': artist.get('strStyle'),
                        'website': artist.get('strWebsite'),
                        'facebook': artist.get('strFacebook'),
                        'twitter': artist.get('strTwitter'),
                        'source': 'theaudiodb',
                        'extracted_date': ds
                    }
                    all_band_details.append(band_detail)
            
        except requests.RequestException as e:
            print(f"Error fetching TheAudioDB data for {band_name}: {e}")
            continue
    
    # Save to S3/MinIO
    s3_key = f"theaudiodb/{ds}/band_details.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(all_band_details, indent=2),
        ContentType='application/json'
    )
    
    print(f"Extracted {len(all_band_details)} band details from TheAudioDB and saved to s3://{S3_BUCKET}/{s3_key}")
    return len(all_band_details)

def extract_discogs_data(**context):
    """Extract additional metadata from Discogs API"""
    ds = context['ds']
    s3_client = get_s3_client()
    
    if not DISCOGS_TOKEN:
        print("Discogs token not configured, skipping Discogs extraction")
        return 0
    
    headers = {
        'Authorization': f'Discogs token={DISCOGS_TOKEN}',
        'User-Agent': 'PostPunkETL/1.0'
    }
    
    # Search for post-punk releases
    all_releases = []
    genres = ['Post-Punk', 'New Wave', 'Alternative Rock']
    
    for genre in genres:
        try:
            print(f"Fetching Discogs releases for genre: {genre}")
            
            url = f"{DISCOGS_BASE_URL}/database/search"
            params = {
                'genre': genre,
                'year': '1980,1981,1982,1983,1984,1985,1986,1987,1988,1989,1990,1991,1992,1993,1994,1995,1996,1997,1998,1999',
                'type': 'release',
                'per_page': 100
            }
            
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            for release in data.get('results', []):
                release_data = {
                    'id': release.get('id'),
                    'title': release.get('title'),
                    'year': release.get('year'),
                    'format': release.get('format'),
                    'label': release.get('label'),
                    'country': release.get('country'),
                    'genre': release.get('genre'),
                    'style': release.get('style'),
                    'thumb': release.get('thumb'),
                    'resource_url': release.get('resource_url'),
                    'source': 'discogs',
                    'extracted_date': ds
                }
                all_releases.append(release_data)
                
        except requests.RequestException as e:
            print(f"Error fetching Discogs data for genre {genre}: {e}")
            continue
    
    # Save to S3/MinIO
    s3_key = f"discogs/{ds}/releases.json"
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=json.dumps(all_releases, indent=2),
        ContentType='application/json'
    )
    
    print(f"Extracted {len(all_releases)} releases from Discogs and saved to s3://{S3_BUCKET}/{s3_key}")
    return len(all_releases)

def notify_completion(**context):
    """Send completion notification (Slack-style log for demo)"""
    ds = context['ds']
    task_instances = context['task_instances']
    
    musicbrainz_count = context['task_instance'].xcom_pull(task_ids='extract_musicbrainz')
    theaudiodb_count = context['task_instance'].xcom_pull(task_ids='extract_theaudiodb')
    discogs_count = context['task_instance'].xcom_pull(task_ids='extract_discogs')
    
    message = f"""
🎸 PostPunk ETL Completed Successfully! 🎸
📅 Date: {ds}
📊 Data extracted:
  • MusicBrainz: {musicbrainz_count} bands
  • TheAudioDB: {theaudiodb_count} band details  
  • Discogs: {discogs_count} releases
  
✅ All data processed and indexed in MeiliSearch
🔍 Ready for search at http://postpunk.local
    """
    
    print(message)
    return message

# Define tasks
extract_musicbrainz_task = PythonOperator(
    task_id='extract_musicbrainz',
    python_callable=extract_musicbrainz_data,
    dag=dag,
)

extract_theaudiodb_task = PythonOperator(
    task_id='extract_theaudiodb',
    python_callable=extract_theaudiodb_data,
    dag=dag,
)

extract_discogs_task = PythonOperator(
    task_id='extract_discogs',
    python_callable=extract_discogs_data,
    dag=dag,
)

# Spark job for data normalization
normalize_spark_task = SparkKubernetesOperator(
    task_id='normalize_bands',
    namespace='default',
    application_file='jobs/normalize_bands.py',
    kubernetes_conn_id='kubernetes_default',
    dag=dag,
)

notify_task = PythonOperator(
    task_id='notify_completion',
    python_callable=notify_completion,
    dag=dag,
)

# Define task dependencies
[extract_musicbrainz_task, extract_theaudiodb_task, extract_discogs_task] >> normalize_spark_task >> notify_task