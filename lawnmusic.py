import subprocess
import os
import re
import json
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# Define filenames for different search types
SEARCH_TRACK_JSON_FILENAME = 'search_track.json'
SEARCH_ALBUM_JSON_FILENAME = 'search_album.json'
DOWNLOAD_OUTPUT_FILE = 'download_log.txt'

def parse_search_json(json_data: list):
    """
    Parses a list of dictionaries from either search_track.json or search_album.json
    to extract item details (title, artist, id, media_type).

    Args:
        json_data (list): The loaded JSON data (list of dictionaries) from a search results file.

    Returns:
        list: A list of dictionaries, where each dict contains 'title', 'artist', 'id', 'media_type'.
              'media_type' will be 'track' or 'album'.
    """
    parsed_items = []

    # Regex to capture title and artist from "Title by Artist" format in 'desc'
    title_artist_pattern = re.compile(r'^(?P<title>.+?)\s*by\s*(?P<artist>.+)$')

    if not isinstance(json_data, list):
        print(f"[{os.path.basename(__file__)}] Warning: Expected a list of search results, but received a different type.")
        return []

    for item in json_data:
        # Ensure essential keys are present and media_type is valid
        if (isinstance(item, dict) and
            'id' in item and
            'desc' in item and
            'media_type' in item and
            item['media_type'] in ['track', 'album']):

            item_id = str(item['id']) # Ensure ID is a string
            desc = item['desc'].strip()
            media_type = item['media_type']
            title = "N/A"
            artist = "N/A"

            # Attempt to parse title and artist from the 'desc' field
            match = title_artist_pattern.match(desc)
            if match:
                title = match.group('title').strip()
                artist = match.group('artist').strip()
            else:
                # If "by" pattern not found, assume the whole desc is the title
                title = desc
                artist = "Unknown Artist" # Or leave as N/A if artist cannot be reliably parsed

            parsed_items.append({
                'title': title,
                'artist': artist,
                'id': item_id,
                'media_type': media_type # Add media_type to the parsed item
            })
        else:
            print(f"[{os.path.basename(__file__)}] Warning: Skipping item with unexpected format or missing required keys: {item}")

    return parsed_items

@app.route('/', methods=['GET', 'POST'])
def index():
    parsed_items = [] # Renamed from parsed_songs to parsed_items
    download_output = None

    # Get current_search_type from form submission or URL parameter, default to 'track'
    current_search_type = request.form.get('search_type', request.args.get('search_type', 'track'))

    # If download_output was passed via redirect (after an item download)
    if 'download_output' in request.args:
        download_output = request.args.get('download_output')

    if request.method == 'POST':
        if 'text_input' in request.form:
            text_input = request.form['text_input']

            # Determine which JSON file to use based on search_type
            if current_search_type == 'album':
                current_json_filename = SEARCH_ALBUM_JSON_FILENAME
                rip_search_media_type = 'album'
            else: # Default to track
                current_json_filename = SEARCH_TRACK_JSON_FILENAME
                rip_search_media_type = 'track'

            # --- Delete old JSON file before new search ---
            if os.path.exists(current_json_filename):
                try:
                    os.remove(current_json_filename)
                    print(f"[{os.path.basename(__file__)}] Deleted existing {current_json_filename}")
                except OSError as e:
                    print(f"[{os.path.basename(__file__)}] Error deleting {current_json_filename}: {e}")
                    output = f"Error: Could not delete old search data ({current_json_filename}). Please check file permissions. Details: {e}"
                    return render_template('index.html', items=parsed_items, download_output=download_output, search_output=output, current_search_type=current_search_type)

            # --- Execute 'rip search' command ---
            rip_command = f"rip search qobuz {rip_search_media_type} '{text_input}' --output-file {current_json_filename}"
            print(f"[{os.path.basename(__file__)}] Executing rip search: {rip_command}")
            rip_process = subprocess.run(rip_command, shell=True, capture_output=True, text=True)

            if rip_process.returncode != 0:
                output = f"Error executing rip search command:\n{rip_process.stderr or 'Unknown error. Check if \'rip\' is installed and accessible.'}"
                print(f"[{os.path.basename(__file__)}] Rip search failed: {output}")
                return render_template('index.html', items=parsed_items, download_output=download_output, search_output=output, current_search_type=current_search_type)
            else:
                print(f"[{os.path.basename(__file__)}] Rip search completed successfully.")

            # --- Directly read and parse the appropriate JSON file ---
            if os.path.exists(current_json_filename):
                try:
                    with open(current_json_filename, 'r', encoding='utf-8') as f:
                        search_data = json.load(f)
                    parsed_items = parse_search_json(search_data) # Use the unified parsing function
                    print(f"[{os.path.basename(__file__)}] Successfully parsed {len(parsed_items)} items from {current_json_filename}.")
                except json.JSONDecodeError as e:
                    output = f"Error: Invalid JSON format in '{current_json_filename}': {e}"
                    print(f"[{os.path.basename(__file__)}] JSON parsing failed: {output}")
                    return render_template('index.html', items=parsed_items, download_output=download_output, search_output=output, current_search_type=current_search_type)
                except Exception as e:
                    output = f"An unexpected error occurred while reading or parsing '{current_json_filename}': {e}"
                    print(f"[{os.path.basename(__file__)}] Unexpected error: {e}")
                    return render_template('index.html', items=parsed_items, download_output=download_output, search_output=output, current_search_type=current_search_type)
            else:
                output = f"Error: '{current_json_filename}' not found after rip search completed."
                print(f"[{os.path.basename(__file__)}] {current_json_filename} not found.")
                return render_template('index.html', items=parsed_items, download_output=download_output, search_output=output, current_search_type=current_search_type)

    # Render the template, passing all relevant data
    return render_template('index.html',
                            items=parsed_items, # Renamed from songs to items
                            download_output=download_output,
                            current_search_type=current_search_type) # Pass the selected type to maintain state

@app.route('/download_item', methods=['POST']) # Renamed route to be generic
def download_item():
    item_id = request.form.get('item_id')
    item_type = request.form.get('item_type') # Get the type of item (track/album)

    if not item_id or not item_type or item_type not in ['track', 'album']:
        return redirect(url_for('index', download_output="Error: Invalid item ID or type provided for download."))

    # Delete old download log file if it exists
    if os.path.exists(DOWNLOAD_OUTPUT_FILE):
        try:
            os.remove(DOWNLOAD_OUTPUT_FILE)
            print(f"[{os.path.basename(__file__)}] Deleted existing {DOWNLOAD_OUTPUT_FILE}")
        except OSError as e:
            print(f"[{os.path.basename(__file__)}] Error deleting {DOWNLOAD_OUTPUT_FILE}: {e}")
            return redirect(url_for('index', download_output=f"Error: Could not delete old download log. Details: {e}"))

    # Construct the rip id command based on item_type
    rip_id_command = f"rip id qobuz {item_type} '{item_id}'"
    print(f"[{os.path.basename(__file__)}] Executing rip id command: {rip_id_command}")

    try:
        with open(DOWNLOAD_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            process = subprocess.run(rip_id_command, shell=True, stdout=f, stderr=subprocess.STDOUT, text=True)

        with open(DOWNLOAD_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            download_log_content = f.read()

        if process.returncode != 0:
            download_output = f"Error during download ({item_type} ID: {item_id}):\n{download_log_content}"
            print(f"[{os.path.basename(__file__)}] Rip ID command failed for {item_type} ID {item_id}:\n{download_output}")
        else:
            download_output = f"Download initiated for {item_type} ID: {item_id}\nLog:\n{download_log_content}"
            print(f"[{os.path.basename(__file__)}] Rip ID command successful for {item_type} ID {item_id}.")

    except Exception as e:
        download_output = f"An unexpected error occurred while trying to download {item_type} {item_id}: {e}"
        print(f"[{os.path.basename(__file__)}] Exception during rip id execution: {e}")

    # Redirect back to the index page, passing the download output
    # Also pass the current_search_type to maintain the toggle state after download
    return redirect(url_for('index', download_output=download_output, search_type=item_type))

if __name__ == '__main__':
    # To make it accessible on your local network, change app.run() to:
    app.run(debug=True, host='0.0.0.0', port=5000)
