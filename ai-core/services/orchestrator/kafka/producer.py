from aiokafka import AIOKafkaProducer
from config import KAFKA_BOOTSTRAP, TOPIC_DLQ
import json


class DlqProducer:
	def __init__(self) -> None:
		self.producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP)
		self._started = False

	async def start(self) -> None:
		if not self._started:
			await self.producer.start()
			self._started = True

	async def stop(self) -> None:
		if self._started:
			await self.producer.stop()
			self._started = False

	async def publish(self, event_id: str, payload: dict, reason: str) -> None:
		key = event_id.encode("utf-8")
		val = json.dumps({"event_id": event_id, "payload": payload, "reason": reason}).encode("utf-8")
		await self.producer.send_and_wait(TOPIC_DLQ, value=val, key=key)


