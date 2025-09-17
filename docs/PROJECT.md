we need to bootstrap a new Python project that makes use of the official gopro python sdk (open-gopro) - we have a reference of the repository cloned under sdk/OpenGoPro. This directory is just a reference and will not be included in the final thing, and is also git-ignored.

the objective of this project is to bootstrap a CLI like codebase that can connect and control the GoPro. We will start by focusing on webcam support - by connecting to the gopro and telling it to enter webcam mode. WE DO NOT WANT TO SETUP ANY V4L2 OR ANY OTHER KIND OF PROCESS THAT CONSUMES THE WEBCAM UDP STREAM FOR NOW. the objective is to simply enable webcam mode with good code patters.

The initial view will be a CLI but keep in mind we will be working on a GTK based view in the future - thus the mvc pattern.

for setting up the webcam, we want to make sure we follow all possible settings to make sure we are reducing delay - see docs/RESEARCH.md for context on that.

For the system that will consume the gopro's webcam stream, let's make this in a way we can specify multiple modes. Historically, projects working with the gopro on linux will setup a v4l2 vistual device and a ffmpeg process that will consume the udp stream from the gopro into a virtual v4l2 device. We will enable that as one of the options for now, but keep in mind I want to experiment creating a pipewire device in the future, skipping all that delay-prone process too.

make sure you are familiar with the SDK and the demos is provides before starting this implementation, and try to follow similar patterns when possible.
