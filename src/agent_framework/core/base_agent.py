# src/agent_framework/core/base_agent.py 

from abc import ABC, abstractmethod
import logging

class BaseAgent(ABC):
    """
    Abstract base class for agents. Agents should follow a simple lifecycle:
    - initialize() any required resources
    - start() their main loop or process
    - stop() gracefully shut down
    - cleanup() free resources if needed
    """
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def initialize(self):
        """Initialize any clients, services, or state before start."""
        pass

    @abstractmethod
    async def start(self):
        """Begin the agent's main operation."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the agent's work gracefully."""
        pass

    async def cleanup(self):
        """Cleanup resources if needed. May be overridden by subclasses."""
        pass

