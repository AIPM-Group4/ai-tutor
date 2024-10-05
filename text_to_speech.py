from whisperspeech.pipeline import Pipeline
import torchaudio
import shutil
from huggingface_hub import hf_hub_download
from pathlib import Path
from argparse import ArgumentParser
import os

MODEL_DIR = 'models/'
OUTPUT_DIR = 'outputs/'

def output_audio(text, lang='fr',
                 s2a_ref='collabora/whisperspeech:s2a-q4-tiny-en+pl.model',
                 t2s_ref='collabora/whisperspeech:t2s-small-en+pl.model'):
    """
    Refer to https://github.com/collabora/WhisperSpeech/tree/main    
    returns a tensor of amplitude values representing audio 
    """
    # Load models
    s2a_filename = get_model_filename(s2a_ref)
    t2s_filename = get_model_filename(t2s_ref)
    pipe = Pipeline(t2s_filename, s2a_ref=s2a_filename)

    # Run inference
    result = pipe.generate(text=text, lang=lang).cpu()
    #pipe.generate_to_file(fname=f'{OUTPUT_DIR}output.wav', text=text, speaker=None, lang='fr')

    # Uncomment to save audio
    #os.makedirs(OUTPUT_DIR, exist_ok = True)
    #torchaudio.save(f'{OUTPUT_DIR}output.wav', result, sample_rate=22050)
    return result

def get_model_filename(ref):
    """
    ref is a huggingface reference (repo:filename).
    If not already saved in local, downloads the model locally.
    Returns file path pointing to the model.
    """
    repo_id, filename = ref.split(":", 1)
    local_filename = f"models/{filename}"
    my_file = Path(local_filename)
    if not my_file.is_file():
        download_hf_model(repo_id, filename)
    return local_filename

def download_hf_model(repo_id, filename):
    temp_filename = hf_hub_download(repo_id=repo_id, filename=filename)
    os.makedirs(MODEL_DIR, exist_ok=True)
    shutil.copy2(temp_filename, MODEL_DIR)
    
    
def main():
    parser = ArgumentParser()
    parser.add_argument('-t', '--text', help='String text to convert to speech.')
    parser.add_argument('-l', '--lang', default='fr', help='Language of the text.')
    args = parser.parse_args()
    output_audio(args.text, args.lang)

if __name__ == "__main__":
    main()
