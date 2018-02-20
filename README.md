Shot Listener was born out of the need to do something.

I taught middle school for 11 years and there is nothing more sacred than a child's life. This meager project is created as a hope to do something in response to the threat.

The goal of the project was to create a Python script that ran on a Raspberry Pi that listened to a few seconds of audio, then parsed it through a Fast Fourier Transform (FFT) engine to determine if there were a match to the unique audio signatures of gunfire.

I "fed" the engine with high-fidelity recordings of gunfire of the weapons used in past mass shootings. 

If and when the system detects a match, it can send a text message with the match percentage to whomever you like, configured in the code.

It works, somewhat. Based on the hardware limitations of the Pi, it can't listen in real time, so there is a 4-5 second lag between listens, which is not ideal.

But it's a start.
