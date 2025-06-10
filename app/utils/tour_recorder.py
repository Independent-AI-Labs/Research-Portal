import argparse
import asyncio
import os
import pathlib
import time

import ffmpeg
from playwright.async_api import async_playwright


async def record_smart_report_tour(report_uri: str, temp_video_path: str, resolution: dict, headless: bool):
    """
    Launches a browser, records a video of the Smart Report tour from a local file,
    saves it to a temporary path, and returns the measured setup time.
    """
    print("🚀 Starting the recording process...")
    async with async_playwright() as p:
        # Start the timer as soon as the context with recording is created
        start_time = time.monotonic()

        print("🖥️  Launching browser...")
        browser = await p.chromium.launch(headless=headless)

        print("📹 Creating new browser context with video recording enabled...")
        context = await browser.new_context(
            record_video_dir="temp_videos/",
            record_video_size={'width': resolution['width'], 'height': resolution['height']},
            viewport={'width': resolution['width'], 'height': resolution['height']}
        )

        print("📄 Creating new page...")
        page = await context.new_page()

        print(f"🧭 Navigating to: {report_uri}")
        await page.goto(report_uri, wait_until='networkidle')
        print("✅ Page loaded and ready.")

        # Give the page a moment to settle before we do anything
        await asyncio.sleep(2)

        tour_button_selector = '#tour-button'
        play_icon_selector = '.fa-play'
        pause_icon_selector = '.fa-pause'

        print("🔍 Searching for the tour button...")
        await page.wait_for_selector(tour_button_selector)
        print("▶️ Tour button found.")

        print("🖱️  Clicking 'Play Tour' button...")
        await page.click(tour_button_selector)

        # Capture the exact time the tour was started
        click_time = time.monotonic()
        setup_duration = click_time - start_time
        print(f"⏱️  Measured setup time to trim: {setup_duration:.2f} seconds.")

        print("⏳ Tour has started. Now waiting for it to complete...")
        await page.wait_for_selector(f"{tour_button_selector} i{pause_icon_selector}")
        print("⏸️  Pause icon detected. Tour is officially running.")

        await page.wait_for_selector(f"{tour_button_selector} i{play_icon_selector}", timeout=600000)
        print("🏁 Play icon detected. Tour has finished.")

        await asyncio.sleep(2)

        print("🛑 Closing browser context...")
        await context.close()

        video_temp_path_raw = await page.video.path()
        os.rename(video_temp_path_raw, temp_video_path)
        print(f"📼 Silent video successfully recorded and stored at: {temp_video_path}")

        # Return the measured setup time for the sync process
        return setup_duration


def merge_audio_and_video(temp_video_path: str, audio_dir: str, num_audio_clips: int, final_output_path: str, trim_start_seconds: float):
    """
    Stitches audio, syncs it with the video by adjusting tempo based on a measured
    setup time, and merges them into a final file.
    """
    print("\n🎶--- Starting audio/video merge and sync process ---")
    try:
        # --- 1. Calculate Audio Duration ---
        audio_inputs = []
        total_audio_duration = 0.0
        print("🔍 Locating audio clips and calculating total duration...")
        for i in range(num_audio_clips):
            clip_path = os.path.join(audio_dir, f"stop_{i}.wav")
            if not os.path.exists(clip_path):
                raise FileNotFoundError(f"Audio file not found: {clip_path}")

            probe = ffmpeg.probe(clip_path)
            duration = float(probe['format']['duration'])
            total_audio_duration += duration
            audio_inputs.append(ffmpeg.input(clip_path))
        print(f"🎧 Found {len(audio_inputs)} audio clips. Total audio duration: {total_audio_duration:.2f}s")

        # --- 2. Use Measured Trim Time to Calculate Video Tour Duration ---
        video_probe = ffmpeg.probe(temp_video_path)
        raw_video_duration = float(video_probe['format']['duration'])
        print(f"📹 Raw silent video duration: {raw_video_duration:.2f}s")

        # This is the actual duration of the visual tour part of the video
        effective_tour_duration = raw_video_duration - trim_start_seconds
        print(f"✂️ Using measured setup time of {trim_start_seconds:.2f}s. Effective tour video duration: {effective_tour_duration:.2f}s")

        # --- 3. Calculate Audio Tempo Adjustment ---
        # This will slightly speed up or slow down the audio to match the video's real-time length.
        # The formula is tempo = audio_duration / video_duration_to_match
        tempo_adjustment_factor = total_audio_duration / effective_tour_duration
        print(f"⚖️  Calculated audio tempo adjustment factor: {tempo_adjustment_factor:.4f}")

        # --- 4. Define FFmpeg Streams with Filters ---
        # Concatenate audio clips
        concatenated_audio = ffmpeg.concat(*audio_inputs, v=0, a=1)
        # Apply the tempo filter to the concatenated audio to match the video's tour length
        synced_audio = ffmpeg.filter(concatenated_audio, 'atempo', tempo_adjustment_factor)

        # Input the video and trim the measured setup time from the start
        video_input = ffmpeg.input(temp_video_path, ss=trim_start_seconds)

        print(f"🎞️  Merging and re-encoding video into '{final_output_path}'...")
        (
            ffmpeg.output(
                video_input['v'],
                synced_audio,
                final_output_path,
                # Set a standard framerate to fix sync issues
                r=30,
                vcodec='libx264',
                acodec='aac',
                shortest=None  # We are handling duration manually
            )
            .run(quiet=False, overwrite_output=True)
        )

        print(f"✅ Final video saved to: {final_output_path}")

    except Exception as e:
        print(f"An error occurred during merge: {e}")
    finally:
        if os.path.exists(temp_video_path):
            print(f"🧹 Cleaning up intermediate file: {temp_video_path}")
            os.remove(temp_video_path)
        if os.path.exists('temp_videos') and not os.listdir('temp_videos'):
            os.rmdir('temp_videos')


def main():
    """Main function to parse arguments and orchestrate the video generation."""
    parser = argparse.ArgumentParser(
        description="Record a video tour of a Smart Report HTML file and merge it with audio.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '-i', '--html-file',
        required=True,
        help='Path to the input Smart Report HTML file.'
    )
    parser.add_argument(
        '-o', '--output-file',
        default='Smart_Report_Tour_FINAL.mp4',
        help='Path for the final output MP4 video. (Default: Smart_Report_Tour_FINAL.mp4)'
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='If specified, the browser will be visible during recording (runs in headed mode).'
    )
    args = parser.parse_args()

    # --- Derive paths from arguments ---
    report_html_path = args.html_file
    if not os.path.exists(report_html_path):
        print(f"Error: Cannot find HTML file at: {report_html_path}")
        return

    report_dir = os.path.dirname(report_html_path)
    audio_dir = os.path.join(report_dir, "Audio")
    if not os.path.exists(audio_dir):
        print(f"Error: Cannot find 'Audio' directory in the same folder as the HTML file: {audio_dir}")
        return

    report_uri = pathlib.Path(report_html_path).as_uri()
    temp_video_dir = "temp_videos"
    temp_video_path = os.path.join(temp_video_dir, "silent_video.webm")

    # --- Execute workflow ---
    if not os.path.exists(temp_video_dir):
        os.makedirs(temp_video_dir)

    # 1. Record silent video and get the exact setup time to trim
    trim_duration = asyncio.run(record_smart_report_tour(
        report_uri=report_uri,
        temp_video_path=temp_video_path,
        resolution={"width": 1920, "height": 1080},
        headless=not args.headed
    ))

    # 2. Merge with audio, passing in the calculated trim duration
    if os.path.exists(temp_video_path) and trim_duration is not None:
        merge_audio_and_video(
            temp_video_path=temp_video_path,
            audio_dir=audio_dir,
            num_audio_clips=10,  # As defined in the report's tourData
            final_output_path=args.output_file,
            trim_start_seconds=trim_duration
        )


if __name__ == "__main__":
    main()
