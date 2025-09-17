"""Stream consumer framework for handling GoPro webcam streams."""

try:
    from .base import StreamConsumer, StreamConsumerType
    from .v4l2_consumer import V4L2Consumer, V4L2ConsumerConfig
    
    __all__ = ["StreamConsumer", "StreamConsumerType", "V4L2Consumer", "V4L2ConsumerConfig"]
except ImportError:
    # Allow module to be imported even if dependencies aren't installed yet
    __all__ = []