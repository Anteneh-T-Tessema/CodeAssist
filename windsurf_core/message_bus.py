# windsurf_core/message_bus.py

import asyncio
from collections import defaultdict
from typing import Any, Callable, Dict, List, Coroutine

class MessageBus:
    """
    A simple in-memory message bus for inter-agent communication.
    Allows for publish-subscribe messaging patterns.
    """

    def __init__(self):
        # Stores subscribers for each channel (event type).
        # The key is the channel name (str), and the value is a list of asyncio.Queue objects.
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._channel_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """
        Allows an agent to subscribe to a specific channel (event type) and receive messages.

        Args:
            channel: The name of the channel to subscribe to.

        Returns:
            An asyncio.Queue object that the subscriber can use to receive messages.
        """
        async with self._channel_locks[channel]:
            queue = asyncio.Queue()
            self._subscribers[channel].append(queue)
            return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue) -> bool:
        """
        Allows an agent to unsubscribe from a specific channel.

        Args:
            channel: The name of the channel to unsubscribe from.
            queue: The asyncio.Queue object that was returned by the subscribe method.

        Returns:
            True if unsubscription was successful, False otherwise (e.g., queue not found).
        """
        async with self._channel_locks[channel]:
            if channel in self._subscribers and queue in self._subscribers[channel]:
                self._subscribers[channel].remove(queue)
                if not self._subscribers[channel]: # Remove channel if no subscribers left
                    del self._subscribers[channel]
                    del self._channel_locks[channel] # Also remove the lock
                return True
            return False

    async def publish(self, channel: str, message: Any) -> None:
        """
        Publishes a message to all subscribers of a specific channel.

        Args:
            channel: The name of the channel to publish the message to.
            message: The message content to be sent.
        """
        # Iterate over a copy of the subscriber list for the channel
        # This is to avoid issues if a subscriber unsubscribes while iterating
        subscribers_copy = []
        async with self._channel_locks[channel]:
            if channel in self._subscribers:
                subscribers_copy = list(self._subscribers[channel])

        for queue in subscribers_copy:
            try:
                await queue.put(message)
            except Exception as e:
                # Handle potential errors during putting message to queue,
                # e.g., queue closed or full, depending on specific queue types if used differently.
                # For a simple asyncio.Queue, put() can raise if the queue is full and non-blocking,
                # but by default, it waits. Here, we'll just log or print.
                print(f"Error publishing to a queue on channel '{channel}': {e}")

# Global instance of the message bus to be used by agents
# This is a simple approach; for larger systems, dependency injection or a service locator might be preferred.
message_bus = MessageBus()

async def main():
    # Example Usage
    async def listener(channel_name: str, id: int):
        queue = await message_bus.subscribe(channel_name)
        print(f"Listener {id} subscribed to {channel_name}")
        try:
            while True:
                message = await queue.get()
                print(f"Listener {id} received on {channel_name}: {message}")
                if message == "stop":
                    break
        finally:
            await message_bus.unsubscribe(channel_name, queue)
            print(f"Listener {id} unsubscribed from {channel_name}")

    async def publisher(channel_name: str):
        await asyncio.sleep(0.1) # Ensure listeners are subscribed
        await message_bus.publish(channel_name, "Hello World!")
        await asyncio.sleep(0.1)
        await message_bus.publish(channel_name, "Another message")
        await asyncio.sleep(0.1)
        await message_bus.publish(channel_name, "stop") # Signal listeners to stop

    # Run example
    print("Starting message bus example...")
    await asyncio.gather(
        listener("test_channel", 1),
        listener("test_channel", 2),
        publisher("test_channel")
    )
    print("Message bus example finished.")

if __name__ == "__main__":
    # To run this example: python -m windsurf_core.message_bus
    # Ensure you are in the parent directory of windsurf_core
    asyncio.run(main())
