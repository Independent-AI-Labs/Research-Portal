# To run this code you need to install the following dependencies:
# pip install google-genai beautifulsoup4

"""
Generates individual audio files for a guided tour based on narration scripts
embedded in an HTML file.

This script parses a specified HTML file to find a 'TourManager.tourData'
JavaScript array. For each tour stop, it combines a style instruction with a
(potentially multi-speaker) narration script and uses the Google Generative AI
API to create a single audio file for that stop's dialogue.

Usage:
  - Basic (uses default values):
    python google_tts.py

  - Specify input file and output directory:
    python google_tts.py --html-file "my_report.html" --audio-dir "Output_Audio"

  - Use a different TTS model:
    python google_tts.py --model "gemini-2.5-flash-preview-tts"
"""

import argparse
import ast
import os
import re
import time
import wave

from bs4 import BeautifulSoup
from google import genai
from google.genai import types


def save_wave_file(file_name, pcm_data, channels=1, rate=24000, sample_width=2):
    """Saves PCM audio data to a WAV file, creating directories if needed."""
    os.makedirs(os.path.dirname(file_name), exist_ok=True)
    with wave.open(file_name, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    print(f"File saved to: {file_name}")


def get_tour_data_from_html(file_path):
    """Parses the HTML file to extract the tour data array."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    scripts = soup.find_all('script')

    for script in scripts:
        if script.string and 'TourManager.init' in script.string:
            match = re.search(r'this\.tourData\s*=\s*(\[.*?\]);', script.string, re.DOTALL)
            if match:
                js_array_string = match.group(1)
                js_array_string = re.sub(r'//.*', '', js_array_string)
                py_literal_string = re.sub(r'([{\s,])([a-zA-Z0-9_]+)\s*:', r'\1"\2":', js_array_string)

                try:
                    tour_data_object = ast.literal_eval(py_literal_string)
                    return tour_data_object
                except (ValueError, SyntaxError) as e:
                    print(f"Error parsing the JavaScript object literal: {e}")
                    print("Cleaned string that failed parsing:\n", py_literal_string)
                    return None

    print(f"Error: Could not find the 'TourManager.tourData' array in {file_path}.")
    return None


def create_speech_config(narration_text):
    """
    Analyzes the narration text to detect speakers and creates appropriate
    speech configuration for multi-speaker TTS.

    Returns tuple: (speech_config, processed_text)
    """
    # Define voice mapping - only these voices are supported
    voice_mapping = {
        "Speaker 1": "Iapetus",
        "Speaker 2": "Gacrux",
    }

    # Look for speaker patterns and preserve order of appearance
    speaker_pattern = r'(Speaker\s*"?\d+"?|[A-Za-z]+):\s*'
    speakers_found = []
    matches = re.findall(speaker_pattern, narration_text)

    for match in matches:
        speaker_name = match.strip()
        speaker_name = re.sub(r'"(\d+)"', r'\1', speaker_name)
        if speaker_name not in speakers_found:
            speakers_found.append(speaker_name)

    print(f"  Detected speakers in order: {speakers_found}")

    # Filter to only supported speakers, maintaining order
    supported_speakers = [s for s in speakers_found if s in voice_mapping]

    if not supported_speakers:
        print(f"  Error: No supported speakers found. Supported speakers: {list(voice_mapping.keys())}")
        return None, narration_text

    print(f"  Processing speakers in order: {supported_speakers}")

    if len(supported_speakers) > 1:
        # Multi-speaker configuration - create in consistent order
        speaker_configs = []
        for speaker in supported_speakers:
            voice_name = voice_mapping[speaker]
            print(f"  Mapping '{speaker}' to voice '{voice_name}'")
            speaker_configs.append(
                types.SpeakerVoiceConfig(
                    speaker=speaker,
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    )
                )
            )

        speech_config = types.SpeechConfig(
            multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                speaker_voice_configs=speaker_configs
            )
        )
    else:
        # Single speaker configuration
        speaker = supported_speakers[0]
        voice_name = voice_mapping[speaker]
        print(f"  Single speaker: Mapping '{speaker}' to voice '{voice_name}'")
        speech_config = types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        )

    return speech_config, narration_text


def generate_audio_for_stop(client, stop, stop_index, output_dir, model_name):
    """Generates a single audio file for a given tour stop object."""
    narration_style = stop.get('narrationStyle', '')
    narration_text = stop.get('narration', '')

    output_file = os.path.join(output_dir, f"stop_{stop_index}.wav")

    if not narration_text:
        print(f"Skipping stop {stop_index} due to missing narration text.")
        return False

    if os.path.exists(output_file):
        print(f"Audio file already exists, skipping: {output_file}")
        return False

    print(f"Generating audio for: {output_file}")
    print(f"  Style: {narration_style}")
    print(f"  Narration text: {narration_text[:100]}...")

    # Create speech configuration
    speech_config, processed_text = create_speech_config(narration_text)

    if speech_config is None:
        print(f"  Error: Could not create speech config for stop {stop_index}")
        return False

    # Combine style instruction with the text
    styled_text = f"{narration_style}\n\n{processed_text}" if narration_style else processed_text

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=styled_text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=speech_config
            )
        )

        if (response.candidates and
                response.candidates[0].content and
                response.candidates[0].content.parts and
                response.candidates[0].content.parts[0].inline_data):

            audio_data = response.candidates[0].content.parts[0].inline_data.data
            save_wave_file(output_file, audio_data)
            return True
        else:
            print(f"Error: No audio data received for {output_file}")
            return False

    except Exception as e:
        print(f"An error occurred while generating audio for '{output_file}': {e}")
        return False


def main():
    """Main function to parse arguments and orchestrate the audio generation process."""
    parser = argparse.ArgumentParser(description="Generate TTS audio files for the Navigating The Nexus infographic.")
    parser.add_argument(
        '-i', '--html-file',
        default='Navigating_The_Nexus_Q2_2025.html',
        help='Path to the input HTML file. (Default: Navigating_The_Nexus_Q2_2025.html)'
    )
    parser.add_argument(
        '-o', '--audio-dir',
        default='Audio',
        help='Directory to save the output audio files. (Default: Audio)'
    )
    parser.add_argument(
        '-m', '--model',
        default='gemini-2.5-flash-preview-tts',
        help='The Generative AI model name to use for TTS. (Default: gemini-2.5-flash-preview-tts)'
    )
    parser.add_argument(
        '-d', '--delay',
        type=int,
        default=5,
        help='Delay in seconds between API requests to avoid rate limiting. (Default: 5)'
    )
    args = parser.parse_args()

    # Get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: The GEMINI_API_KEY environment variable is not set.")
        return

    client = genai.Client(api_key=api_key)

    tour_data = get_tour_data_from_html(args.html_file)
    if not tour_data:
        return

    print(f"Using output directory: '{args.audio_dir}'")
    print(f"Using model: '{args.model}'")
    print(f"Using delay: {args.delay} seconds")
    print(f"Supported speakers: Speaker 1 (Iapetus), Speaker 2 (Gacrux)")
    print(f"\nFound {len(tour_data)} tour stops to process from {args.html_file}.")

    # Process each stop
    success_count = 0
    for stop_index, stop in enumerate(tour_data):
        print(f"\n--- Processing Stop {stop_index} ---")
        was_successful = generate_audio_for_stop(
            client=client,
            stop=stop,
            stop_index=stop_index,
            output_dir=args.audio_dir,
            model_name=args.model
        )

        if was_successful:
            success_count += 1
            if args.delay > 0 and stop_index < len(tour_data) - 1:
                print(f"Waiting {args.delay} seconds to avoid rate limiting...")
                time.sleep(args.delay)

    print(f"\nAudio generation process complete. Successfully generated {success_count} audio files.")


if __name__ == "__main__":
    main()
