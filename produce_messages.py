from kafka import KafkaProducer
import time

bootstrap = 'localhost:9092'
topic = 'weather_raw'

producer = KafkaProducer(
    bootstrap_servers=bootstrap,
    value_serializer=lambda v: v.encode('utf-8')
)

rows = [
    "2025-10-17,39.1031,-84.5120,24.5,18.2,5.3,180",
    "2025-10-18,39.1031,-84.5120,25.1,19.1,4.8,175",
    "2025-10-19,39.1031,-84.5120,23.8,17.5,6.1,190"
]

for r in rows:
    print(f"Producing: {r}")
    producer.send(topic, value=r)
    producer.flush()
    time.sleep(1)

producer.close()
print('Done producing sample messages.')