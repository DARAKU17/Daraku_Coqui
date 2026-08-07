#!/usr/bin/env bash
# Example CLI usage for ChronoVoice.

# 1. Check the backend is healthy.
chronovoice health

# 2. Show the effective configuration.
chronovoice config

# 3. List registered voices.
chronovoice voices list

# 4. Add a new voice from a reference clip (name and clip are positional).
chronovoice voices add my_voice /path/to/reference.wav --language en

# 5. Synthesise narration text with the default voice.
chronovoice synth "Here's the twist. My clone voice works."

# 6. Synthesise with a specific voice and output file.
chronovoice synth "Congratulations, you made it." --voice daraku --output out.wav