"""Stream consumer framework for handling GoPro webcam streams."""

try:
    from .base import StreamConsumer, StreamConsumerType
    from .v4l2_consumer import V4L2Consumer, V4L2ConsumerConfig
    from .pipewire_consumer import PipeWireConsumer, PipeWireConsumerConfig
    
    __all__ = ["StreamConsumer", "StreamConsumerType", "V4L2Consumer", "V4L2ConsumerConfig", 
               "PipeWireConsumer", "PipeWireConsumerConfig"]
except ImportError:
    # Allow module to be imported even if dependencies aren't installed yet
    __all__ = []