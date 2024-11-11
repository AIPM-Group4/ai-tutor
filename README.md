# ai-tutor

# code explanations
- prototype.py
    - basic UI with streamlit
- speech_to_text.py
    - create text from uploaded audio
- dialogue.py
    - create response using LLM API
- audio_processing.py
    - process audio

# python version and packages
Python 3.12.6

# install necessary libraries
pip install -r requirements.txt

# run 
streamlit run prototype.py

# aitutor_basic with LiveKit
First set up Sandbox app locally as well as CLI : https://cloud.livekit.io/projects/p_5t2ooezutnl/sandbox

Then : 
cd <aitutor_basic>

python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
python3 agent.py dev

# Streaming (speech-to-speech pipeline)(not used)
pip install faster-whisper
pip install torch torchvision torchaudio
pip install rich
pip install deepfilternet
pip install git+https://github.com/andimarafioti/MeloTTS.git#egg=MeloTTS
