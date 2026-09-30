import unittest

from realtime.sse_manager import SSEManager


class SSEManagerTests(unittest.IsolatedAsyncioTestCase):
    async def test_replays_events_published_before_subscription(self):
        manager = SSEManager()
        event = {"event_id": "evt_person", "type": "person_detected"}

        await manager.publish(event)
        queue = await manager.subscribe()

        self.assertEqual(queue.get_nowait(), event)

    async def test_replay_history_is_bounded(self):
        manager = SSEManager(history_size=2)

        await manager.publish({"event_id": "evt_1"})
        await manager.publish({"event_id": "evt_2"})
        await manager.publish({"event_id": "evt_3"})
        queue = await manager.subscribe()

        self.assertEqual(queue.get_nowait(), {"event_id": "evt_2"})
        self.assertEqual(queue.get_nowait(), {"event_id": "evt_3"})
        self.assertTrue(queue.empty())


if __name__ == "__main__":
    unittest.main()
