# NiFi Flow — Weather Ingestion & Connection to Spark

This document describes the main NiFi workflow used in this project and explains how it integrates with the Spark Structured Streaming job (`spark-apps/process_weather.py`). Two illustrative diagrams are included in this document to make the flow clear.

## Overview

Purpose: use Apache NiFi to ingest or transform incoming weather CSV rows and publish them to Kafka for downstream processing by Spark. NiFi can also be used to fetch the cleaned output files that Spark writes to disk for further routing, archival, or downstream systems.

High-level options in this project:
- NiFi acts as a producer into Kafka (PublishKafka) writing plain CSV rows to the `weather_raw` topic. Spark reads from this topic and performs parsing/cleaning.
- Alternatively (or additionally), NiFi can tail or list files under the `data/clean_weather` directory (which Spark writes to) and route or push those cleaned files to other systems.

The canonical flow used for demonstration in this repository is: External data source → NiFi → Kafka topic `weather_raw` → Spark Structured Streaming → cleaned CSV files under `data/clean_weather`.

---

## NiFi processors and recommended configuration

Below are the commonly used NiFi processors for the flows in this repository. Exact field names and NiFi versions may vary slightly.

1. Ingest / Receive
   - Use `ListenHTTP` or `ListenTCP` or `GetFile` depending on your source.
   - Configure appropriate ports, SSL (if needed), and path/headers.

2. (Optional) Parse / Convert
   - `ConvertRecord` or `ExtractText` to parse CSV rows into attributes or records if you need routing based on fields.
   - Use a CSVReader controller service and configure schema if using `ConvertRecord`.

3. Publish to Kafka (main path)
   - `PublishKafka` (NiFi 1.x) or `PublishKafkaRecord` — write each CSV row as a string value to topic `weather_raw`.
   - Kafka Properties:
     - Kafka Brokers: if NiFi runs on the host, use `localhost:9094` (Compose mapping) by default for this repo; if NiFi runs inside the same Docker network use `kafka:9092`.
     - Topic Name: `weather_raw`.
     - Key/Value Serializer: `StringSerializer` for values (and keys if you set them).
   - Set `Delivery Guarantee` and retries according to your reliability needs.

4. Route / Archive
   - After PublishKafka, you can route a copy to `PutFile` to maintain an archive under `data/raw_ingest` (optional) or to `UpdateAttribute` for metadata tagging.

5. (Optional) Consume cleaned files
   - If you need to process Spark's cleaned CSV output, use `ListFile` + `FetchFile` (or `GetFile`) pointed at the mounted path where Spark writes: `/data/clean_weather` (when NiFi runs in a container that mounts the same host path) or the repository `./data/clean_weather` if running on the host.
   - You can then `PutDatabaseRecord`, `PutS3Object`, or `PublishKafka` to move cleaned records further.

---

## How NiFi connects to the Spark job (details)

1. NiFi → Kafka → Spark (primary path)
   - NiFi publishes plain CSV rows into Kafka topic `weather_raw` (see `PublishKafka` processor configuration above).
   - The Spark Structured Streaming job `process_weather.py` uses Spark's Kafka integration:
     - In the repo Spark job sets `kafka_bootstrap = "kafka:9092"` when run inside the Docker Compose network.
     - Spark uses `spark.readStream.format("kafka")` and subscribes to topic `weather_raw`.
   - Ensure the producer (NiFi) writes values as plain CSV strings — Spark's job expects a single string value per message and splits on commas.

2. Socket / File-level integration (alternate)
   - Spark writes cleaned CSV files to `/data/clean_weather` (mounted to the repo `./data/clean_weather` by the Compose file).
   - NiFi can be configured to watch that directory and pick up `part-*` files for further processing (e.g., analytics, S3, database ingest).
   - Processor chain example: `ListFile` (path: `/data/clean_weather`) → `FetchFile` → `PutS3Object` or `PutHDFS` depending on target.

---

## Example NiFi flow (recommended simple setup)

This simple flow demonstrates ingestion from an external HTTP endpoint and publishing to Kafka:

[ListenHTTP] -> [ConvertRecord / RouteOnAttribute] -> [PublishKafka]

- ListenHTTP receives POSTed CSV rows.
- ConvertRecord validates CSV and maps fields if desired.
- PublishKafka pushes validated rows to `weather_raw`.

See the included diagram below: `nifi_flow_diagram.svg`.

---

## Operation notes & troubleshooting

- Bootstrap server mismatch: when NiFi runs on the Windows host, use `localhost:9094` to reach the Kafka broker mapped in `docker-compose.yml`. When NiFi runs inside the Compose network (e.g., as a container), use `kafka:9092`.

- Topic existence: the `create_topic.bat` helper inside this repo creates the `weather_raw` topic using `docker compose exec kafka ...` so the topic exists inside the cluster; NiFi can publish to a topic that already exists or allow Kafka auto-create if enabled.

- Message format: Spark expects a single string CSV per Kafka record. If NiFi publishes JSON or Avro, update `process_weather.py` to use the correct parsing or add a `ConvertRecord` in NiFi that emits plain CSV strings.

- NiFi credentials: this repo contains `nifi_flow_settings.txt` with generated credentials. Treat these as sensitive — don't publish them publicly. Use them to sign in to the NiFi UI and verify processors.

- File permissions: when NiFi runs in a container and writes to host-mounted directories, ensure the container user has write/read permissions for the `data/` mount points.

---

## Diagrams

Overall NiFi flow (ingest → Kafka → Spark):

![NiFi flow diagram](./nifi_flow_diagram.svg)

NiFi to Spark connection detail:

![NiFi to Spark connection](./nifi_to_spark.svg)

---

## Quick checklist to wire NiFi with this repo

- [ ] Start the Docker Compose stack (Zookeeper, Kafka, Spark).
- [ ] Create the `weather_raw` topic (run `create_topic.bat` or create via NiFi if preferred).
- [ ] Configure NiFi `PublishKafka` with correct bootstrap server (host or internal) and `weather_raw` as topic.
- [ ] Start NiFi data ingestion and verify messages land in the Kafka topic (use Kafka consumer or `consume_topic.bat`).
- [ ] Start the Spark job (from `spark-master` container) and verify `data/clean_weather` files are produced.
- [ ] Optionally configure NiFi `ListFile/FetchFile` on `data/clean_weather` to take further action on cleaned files.

---

If you'd like, I can also provide:
- Step-by-step NiFi UI screenshots showing exact processor properties to set.
- A NiFi template XML export for the flow so you can import it into NiFi directly.

