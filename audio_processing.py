import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa

def process_speech_to_text(audio_file_path):
    # Load the latest Whisper model and processor
    processor = WhisperProcessor.from_pretrained("openai/whisper-small")
    model = WhisperForConditionalGeneration.from_pretrained("openai/whisper-small")

    # Load audio file
    print("Loading audio file...")
    audio_input, sr = librosa.load(audio_file_path, sr=16000)

    # Process the audio input
    print("Processing audio input...")
    input_features = processor(audio_input, sampling_rate=sr, return_tensors="pt").input_features

    # Generate token ids
    print("Generating token ids...")
    predicted_ids = model.generate(input_features)

    # Decode token ids to text
    print("Decoding token ids to text...")
    transcription = processor.batch_decode(predicted_ids, skip_special_tokens=True)

    return transcription[0]

# Example usage
print("Processing audio file...")
transcribed_text = process_speech_to_text("New Recording 38.m4a")
print("Transcription complete.")
print(transcribed_text)
