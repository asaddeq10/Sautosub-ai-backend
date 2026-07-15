from faster_whisper import WhisperModel

print("===================================")
print("      AutoSub AI")
print(" Loading Faster Whisper Model...")
print("===================================")

model = WhisperModel(
    "small",
    device="cpu",
    compute_type="int8"
)

print("\n✅ Model loaded successfully!")
print("AutoSub AI is ready for transcription.")
