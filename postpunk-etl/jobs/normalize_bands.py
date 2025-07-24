"""
Spark Job: Normalize PostPunk Bands Data
Reads raw JSON from S3/MinIO, transforms to standard schema, writes to MongoDB and MeiliSearch
"""
import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
import json
import requests
from pymongo import MongoClient
from datetime import datetime

# Configuration
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'minio:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
S3_BUCKET = 'postpunk-raw'

MONGO_HOST = os.getenv('MONGO_HOST', 'mongodb')
MONGO_PORT = int(os.getenv('MONGO_PORT', '27017'))
MONGO_DB = 'postpunk'
MONGO_COLLECTION = 'bands_raw'

MEILISEARCH_HOST = os.getenv('MEILISEARCH_HOST', 'meilisearch')
MEILISEARCH_PORT = int(os.getenv('MEILISEARCH_PORT', '7700'))
MEILISEARCH_INDEX = 'bands_search'

def create_spark_session():
    """Create Spark session with S3 configuration"""
    spark = SparkSession.builder \
        .appName("PostPunk-Normalize-Bands") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .config("spark.hadoop.fs.s3a.endpoint", f"http://{MINIO_ENDPOINT}") \
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("WARN")
    return spark

def read_source_data(spark, ds):
    """Read raw JSON data from all sources"""
    
    # Define paths
    musicbrainz_path = f"s3a://{S3_BUCKET}/musicbrainz/{ds}/"
    theaudiodb_path = f"s3a://{S3_BUCKET}/theaudiodb/{ds}/"
    discogs_path = f"s3a://{S3_BUCKET}/discogs/{ds}/"
    
    dfs = {}
    
    try:
        # Read MusicBrainz data
        musicbrainz_df = spark.read.option("multiline", "true").json(musicbrainz_path)
        if musicbrainz_df.count() > 0:
            dfs['musicbrainz'] = musicbrainz_df
            print(f"Loaded {musicbrainz_df.count()} MusicBrainz records")
    except Exception as e:
        print(f"Could not load MusicBrainz data: {e}")
    
    try:
        # Read TheAudioDB data
        theaudiodb_df = spark.read.option("multiline", "true").json(theaudiodb_path)
        if theaudiodb_df.count() > 0:
            dfs['theaudiodb'] = theaudiodb_df
            print(f"Loaded {theaudiodb_df.count()} TheAudioDB records")
    except Exception as e:
        print(f"Could not load TheAudioDB data: {e}")
    
    try:
        # Read Discogs data
        discogs_df = spark.read.option("multiline", "true").json(discogs_path)
        if discogs_df.count() > 0:
            dfs['discogs'] = discogs_df
            print(f"Loaded {discogs_df.count()} Discogs records")
    except Exception as e:
        print(f"Could not load Discogs data: {e}")
    
    return dfs

def normalize_musicbrainz_data(df):
    """Transform MusicBrainz data to standard schema"""
    
    # Flatten releases array
    releases_df = df.select(
        col("id").alias("band_id"),
        col("name").alias("band"),
        col("country"),
        col("begin_date").alias("year_start"),
        col("end_date").alias("year_end"),
        col("source"),
        col("extracted_date"),
        explode_outer(col("releases")).alias("release")
    )
    
    # Extract release information
    normalized_df = releases_df.select(
        concat(col("band_id"), lit("_"), coalesce(col("release.id"), lit("unknown"))).alias("id"),
        lit("musicbrainz").alias("source"),
        col("band"),
        col("country"),
        regexp_extract(col("year_start"), r"(\d{4})", 1).cast("int").alias("year_start"),
        regexp_extract(col("year_end"), r"(\d{4})", 1).cast("int").alias("year_end"),
        coalesce(col("release.title"), lit("")).alias("album"),
        regexp_extract(col("release.first-release-date"), r"(\d{4})", 1).cast("int").alias("release_date"),
        lit("").alias("member"),
        lit("").alias("role"),
        lit("").alias("track"),
        lit(0).alias("hit_rank"),
        coalesce(col("release.disambiguation"), lit("")).alias("description"),
        current_timestamp().alias("processed_date")
    )
    
    return normalized_df

def normalize_theaudiodb_data(df):
    """Transform TheAudioDB data to standard schema"""
    
    normalized_df = df.select(
        concat(lit("audiodb_"), col("id")).alias("id"),
        lit("theaudiodb").alias("source"),
        col("name").alias("band"),
        col("country"),
        col("formed_year").cast("int").alias("year_start"),
        lit(None).cast("int").alias("year_end"),
        lit("").alias("album"),
        lit(None).cast("int").alias("release_date"),
        lit("").alias("member"),
        lit("").alias("role"),
        lit("").alias("track"),
        lit(0).alias("hit_rank"),
        coalesce(col("biography"), col("style"), col("genre"), lit("")).alias("description"),
        current_timestamp().alias("processed_date")
    )
    
    return normalized_df

def normalize_discogs_data(df):
    """Transform Discogs data to standard schema"""
    
    normalized_df = df.select(
        concat(lit("discogs_"), col("id")).alias("id"),
        lit("discogs").alias("source"),
        regexp_extract(col("title"), r"^([^-]+)", 1).alias("band"),
        col("country"),
        lit(None).cast("int").alias("year_start"),
        lit(None).cast("int").alias("year_end"),
        regexp_extract(col("title"), r" - (.+)$", 1).alias("album"),
        col("year").cast("int").alias("release_date"),
        lit("").alias("member"),
        lit("").alias("role"),
        lit("").alias("track"),
        lit(0).alias("hit_rank"),
        concat_ws(" | ", col("format"), col("label"), col("style")).alias("description"),
        current_timestamp().alias("processed_date")
    )
    
    return normalized_df

def write_to_mongodb(df):
    """Write normalized data to MongoDB"""
    try:
        # Convert Spark DataFrame to Pandas for easier MongoDB insertion
        pandas_df = df.toPandas()
        
        # Connect to MongoDB
        client = MongoClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}/')
        db = client[MONGO_DB]
        collection = db[MONGO_COLLECTION]
        
        # Clear existing data for this date
        collection.delete_many({})
        
        # Insert new data
        records = pandas_df.to_dict('records')
        if records:
            collection.insert_many(records)
            print(f"Inserted {len(records)} records into MongoDB collection {MONGO_COLLECTION}")
        
        client.close()
        
    except Exception as e:
        print(f"Error writing to MongoDB: {e}")

def write_to_meilisearch(df):
    """Write normalized data to MeiliSearch"""
    try:
        # Convert Spark DataFrame to Pandas
        pandas_df = df.toPandas()
        
        # Convert to dictionary records
        records = pandas_df.to_dict('records')
        
        # Convert datetime objects to strings for JSON serialization
        for record in records:
            for key, value in record.items():
                if hasattr(value, 'isoformat'):
                    record[key] = value.isoformat()
                elif pd.isna(value):
                    record[key] = None
        
        if not records:
            print("No records to index in MeiliSearch")
            return
        
        # Configure MeiliSearch
        meilisearch_url = f"http://{MEILISEARCH_HOST}:{MEILISEARCH_PORT}"
        
        # Create/update index
        index_url = f"{meilisearch_url}/indexes/{MEILISEARCH_INDEX}"
        index_config = {
            "uid": MEILISEARCH_INDEX,
            "primaryKey": "id"
        }
        
        response = requests.post(f"{meilisearch_url}/indexes", json=index_config)
        if response.status_code not in [200, 201, 202]:
            print(f"Index creation response: {response.status_code}")
        
        # Configure searchable attributes
        searchable_attributes = [
            "band", "album", "track", "member", "country", "description"
        ]
        
        settings_url = f"{index_url}/settings"
        settings = {
            "searchableAttributes": searchable_attributes,
            "filterableAttributes": ["source", "year_start", "year_end", "release_date", "country"],
            "sortableAttributes": ["year_start", "release_date", "band"]
        }
        
        requests.patch(settings_url, json=settings)
        
        # Bulk upsert documents
        documents_url = f"{index_url}/documents"
        response = requests.post(documents_url, json=records)
        
        if response.status_code in [200, 201, 202]:
            print(f"Successfully indexed {len(records)} records in MeiliSearch")
        else:
            print(f"Error indexing to MeiliSearch: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error writing to MeiliSearch: {e}")

def main():
    """Main processing function"""
    # Get execution date from environment or use current date
    ds = os.getenv('AIRFLOW_DS', datetime.now().strftime('%Y-%m-%d'))
    print(f"Processing data for date: {ds}")
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Read source data
        source_dfs = read_source_data(spark, ds)
        
        if not source_dfs:
            print("No source data found. Exiting.")
            return
        
        # Normalize each source
        normalized_dfs = []
        
        if 'musicbrainz' in source_dfs:
            print("Normalizing MusicBrainz data...")
            mb_normalized = normalize_musicbrainz_data(source_dfs['musicbrainz'])
            normalized_dfs.append(mb_normalized)
        
        if 'theaudiodb' in source_dfs:
            print("Normalizing TheAudioDB data...")
            adb_normalized = normalize_theaudiodb_data(source_dfs['theaudiodb'])
            normalized_dfs.append(adb_normalized)
        
        if 'discogs' in source_dfs:
            print("Normalizing Discogs data...")
            discogs_normalized = normalize_discogs_data(source_dfs['discogs'])
            normalized_dfs.append(discogs_normalized)
        
        # Union all normalized data
        if normalized_dfs:
            final_df = normalized_dfs[0]
            for df in normalized_dfs[1:]:
                final_df = final_df.union(df)
            
            # Remove duplicates and null bands
            final_df = final_df.filter(col("band").isNotNull() & (col("band") != "")) \
                              .dropDuplicates(["band", "album", "source"])
            
            print(f"Total normalized records: {final_df.count()}")
            
            # Show sample data
            print("Sample normalized data:")
            final_df.show(10, truncate=False)
            
            # Write to MongoDB
            print("Writing to MongoDB...")
            write_to_mongodb(final_df)
            
            # Write to MeiliSearch
            print("Writing to MeiliSearch...")
            write_to_meilisearch(final_df)
            
            print("Data normalization and loading completed successfully!")
        
    except Exception as e:
        print(f"Error in main processing: {e}")
        raise
    
    finally:
        spark.stop()

if __name__ == "__main__":
    main()