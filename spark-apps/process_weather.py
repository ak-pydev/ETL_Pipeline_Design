from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    split, col, to_timestamp, current_timestamp, trim, coalesce
)
from pyspark.sql.types import DoubleType

# ---------- Spark Session ----------
spark = (
    SparkSession.builder
        .appName("weather_kafka_etl")
        # If you ever want old date parsing behavior, uncomment:
        # .config("spark.sql.legacy.timeParserPolicy", "LEGACY")
        .getOrCreate()
)

# ---------- Kafka Source ----------
kafka_bootstrap = "kafka:9092"
topic = "weather_raw"

raw_df = (
    spark.readStream.format("kafka")
         .option("kafka.bootstrap.servers", kafka_bootstrap)
         .option("subscribe", topic)
         .option("startingOffsets", "earliest")
         .load()
)

value_df = raw_df.selectExpr("CAST(value AS STRING) as csv_value")
parts = split(col("csv_value"), ",")

df = value_df.select(
    trim(parts.getItem(0)).alias("timestamp"),
    trim(parts.getItem(1)).alias("latitude"),
    trim(parts.getItem(2)).alias("longitude"),
    trim(parts.getItem(3)).alias("temperature_max"),
    trim(parts.getItem(4)).alias("temperature_min"),
    trim(parts.getItem(5)).alias("windspeed"),
    trim(parts.getItem(6)).alias("winddirection")
)

clean_df = (
    df
    .withColumn("latitude",       col("latitude").cast(DoubleType()))
    .withColumn("longitude",      col("longitude").cast(DoubleType()))
    .withColumn("temperature_max", col("temperature_max").cast(DoubleType()))
    .withColumn("temperature_min", col("temperature_min").cast(DoubleType()))
    .withColumn("windspeed",       col("windspeed").cast(DoubleType()))
    .withColumn("winddirection",   col("winddirection").cast(DoubleType()))
    .withColumn(
        "event_time",
        coalesce(
            to_timestamp(col("timestamp"), "yyyy-MM-dd"),
            to_timestamp(col("timestamp"), "yyyy/MM/dd"),
            to_timestamp(col("timestamp"), "yyyy-MM-dd HH:mm:ss"),
            to_timestamp(col("timestamp"), "yyyy/MM/dd HH:mm:ss")
        )
    )
    .withColumn("ingest_ts", current_timestamp())
    .filter(
        col("event_time").isNotNull()
        & col("latitude").isNotNull()
        & col("longitude").isNotNull()
    )
)

query = (
    clean_df.writeStream
        .outputMode("append")
        .format("csv")
        .option("header", "true")
        .option("path", "/data/clean_weather")
        .option("checkpointLocation", "/data/checkpoints/weather_etl")
        .trigger(processingTime="10 seconds")
        .start()
)

query.awaitTermination()

#Spark-job
'''
docker compose exec spark-master bash -lc '
/opt/spark/bin/spark-submit \
  --conf spark.jars.ivy=/tmp/.ivy2 \
  --master spark://spark-master:7077 \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.2 \
  /opt/spark-apps/process_weather.py
'

'''

# Kafka stream new data mounted to /data/clean_weather

'''
New-Item -ItemType Directory -Force -Path "data/clean_weather"
New-Item -ItemType Directory -Force -Path "data/checkpoints/weather_etl"

'''